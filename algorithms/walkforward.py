"""Optimización de variables ROBUSTA: walk-forward + meseta de parámetros + optimización bayesiana.

Por cada algoritmo y cada pliegue (ventanas móviles en el tiempo):
  1. ENTRENAMIENTO: búsqueda bayesiana (TPE de Optuna) de las variables de `genes.cfg`/`gene_ranges.cfg` sobre
     carteras de 20 acciones sorteadas dentro de la ventana de entrenamiento. Objetivo = alpha de timing medio
     (ver metrics.py). La primera evaluación es la configuración actual, así que nunca se parte peor.
  2. MESETA: de los mejores candidatos se elige el de mejor entorno, no el de mejor pico: cada candidato se evalúa
     también con vecinos (todos los parámetros numéricos movidos al azar hasta ±10%) y se queda el de mayor promedio
     (candidato + vecinos). Si un valor deja de funcionar al moverlo un 10%, es sobreajuste.
  3. PRUEBA FUERA DE MUESTRA: en la ventana siguiente (carteras nuevas, nunca vistas) se comparan tres variantes:
     la configuración actual, el mejor "pico" y la "meseta" elegida.
El periodo desde `holdout_start` está reservado: solo se toca con `--stage final`, que reentrena con los últimos
`train_years` previos y evalúa UNA vez en ese periodo.

Uso:  python -m algorithms.walkforward algorithm03a_v1 algorithm01b [--stage walkforward|final] [--workers 6] [--tag x]
"""
from __future__ import annotations

import argparse
import ast
import gc
import json
import multiprocessing as mp
import zlib
import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ticker2db import StockDB

from .engine import OHLC, load_cfg
from .genetic import Gene, load_genes, load_ga_config, make_algo
from .metrics import bootstrap_ci
from .portfolio import PortfolioConfig, backtest_portfolio, load_portfolio_config, sample_portfolio_test

HERE = Path(__file__).parent
PENALTY = -50.0


@dataclass
class WFConfig:
    data_start: str = "1990-01-01"
    holdout_start: str = "2024-01-01"
    train_years: int = 10
    test_years: int = 3
    step_years: int = 3
    train_tests: int = 16
    test_tests: int = 24
    trials: int = 60
    top_candidates: int = 8
    neighbors: int = 6
    perturbation: float = 0.10
    min_trades: int = 20
    seed: int = 2026
    radius: Optional[float] = None   # None = buscar en todo el rango; 0.3 = solo ±30% alrededor de los valores actuales


def load_wf_config(path=HERE / "walkforward.cfg", **over) -> WFConfig:
    v = load_cfg(path, "walkforward") if Path(path).exists() else {}
    v = {k: (str(x) if k in ("data_start", "holdout_start") else x) for k, x in v.items()}
    v.update(over)
    return WFConfig(**v)


def make_folds(wf: WFConfig) -> List[dict]:
    """Pliegues deslizantes: entrenar `train_years`, probar los `test_years` siguientes, avanzar `step_years`."""
    folds, start = [], pd.Timestamp(wf.data_start)
    hold = pd.Timestamp(wf.holdout_start)
    while True:
        tr_end = start + pd.DateOffset(years=wf.train_years) - pd.Timedelta(days=1)
        te_start = tr_end + pd.Timedelta(days=1)
        te_end = te_start + pd.DateOffset(years=wf.test_years) - pd.Timedelta(days=1)
        if te_end >= hold:
            break
        folds.append({"id": len(folds), "train": (start, tr_end), "test": (te_start, te_end)})
        start = start + pd.DateOffset(years=wf.step_years)
    return folds


def final_fold(wf: WFConfig) -> dict:
    hold = pd.Timestamp(wf.holdout_start)
    return {"id": "final", "train": (hold - pd.DateOffset(years=wf.train_years), hold - pd.Timedelta(days=1)),
            "test": (hold, pd.Timestamp("2100-01-01"))}


# ----------------------------- búsqueda -----------------------------
def evaluate(name: str, genome: dict, tests: list, pc: PortfolioConfig):
    """Alpha de timing medio (y por prueba) y operaciones totales de `genome` en las carteras `tests`."""
    algo = make_algo(name)
    for k, v in genome.items():
        setattr(algo.p, k, v)
    alphas, trades, expo = [], 0, []
    for k, (syms, frames, sb) in enumerate(tests):
        m = backtest_portfolio(algo, frames, sb, pc.max_positions, pc.initial_capital, seed=k).metrics
        alphas.append(m["alpha_timing_%"]); trades += m["operaciones"]; expo.append(m["exposicion_%"])
    return float(np.mean(alphas)), trades, alphas, float(np.mean(expo))


def score_train(name, genome, tests, pc, wf) -> float:
    s, trades, _, _ = evaluate(name, genome, tests, pc)
    return s if trades >= wf.min_trades else PENALTY


def _bounds(gene: Gene, cur, radius: Optional[float]):
    """Rango de búsqueda de un gen numérico: todo el rango, o ±radius alrededor del valor actual."""
    lo, hi = float(gene.min), float(gene.max)
    if radius is None or cur is None:
        return lo, hi
    span = abs(cur) * radius if cur != 0 else (hi - lo) * radius
    if gene.type == "int":
        span = max(span, 1.0)
    return max(lo, cur - span), min(hi, cur + span)


def _suggest(trial, genes: List[Gene], current: dict, radius: Optional[float] = None) -> dict:
    g = {}
    for gene in genes:
        cur = current[gene.name]
        if radius is not None:                      # región de confianza: booleanos y None quedan como están
            if gene.type == "bool" or cur is None:
                g[gene.name] = cur
                continue
        none = gene.allow_none and (radius is None) and trial.suggest_categorical(f"{gene.name}__none", [False, True])
        if gene.type == "bool":
            g[gene.name] = trial.suggest_categorical(gene.name, [False, True])
            continue
        lo, hi = _bounds(gene, cur, radius)
        if gene.type == "int":
            v = trial.suggest_int(gene.name, int(round(lo)), int(round(hi)))
        else:
            v = trial.suggest_float(gene.name, lo, hi)
        g[gene.name] = None if none else (v if gene.type == "int" else round(v, 4))
    return g


def _enqueue_params(genes: List[Gene], current: dict, radius: Optional[float] = None) -> dict:
    p = {}
    for gene in genes:
        v = current[gene.name]
        if radius is not None and (gene.type == "bool" or v is None):
            continue                                # fijo: no es un parámetro de la búsqueda
        if gene.allow_none:
            p[f"{gene.name}__none"] = v is None
        if gene.type == "bool":
            p[gene.name] = bool(v)
        else:
            p[gene.name] = (gene.min + gene.max) / 2 if v is None else v
            if gene.type == "int":
                p[gene.name] = int(round(p[gene.name]))
    return p


def _genome_from(trial_params: dict, genes: List[Gene], current: dict) -> dict:
    g = {}
    for gene in genes:
        if gene.name not in trial_params:           # gen fijo (región de confianza): conserva el valor actual
            g[gene.name] = current[gene.name]
            continue
        v = trial_params[gene.name]
        if gene.allow_none and trial_params.get(f"{gene.name}__none"):
            v = None
        g[gene.name] = v if gene.type == "bool" or v is None else (int(v) if gene.type == "int" else round(float(v), 4))
    return g


def perturb(genome: dict, genes: List[Gene], rng: random.Random, frac: float) -> dict:
    """Vecino: todos los parámetros numéricos movidos al azar hasta ±frac a la vez (booleanos y None no cambian)."""
    out = dict(genome)
    for gene in genes:
        v = out[gene.name]
        if v is None or gene.type == "bool":
            continue
        nv = v * (1 + rng.uniform(-frac, frac)) if v != 0 else rng.uniform(-frac, frac) * (gene.max - gene.min)
        if gene.type == "int":
            nv = int(round(nv))
            if nv == v:
                nv = v + rng.choice([-1, 1])
        out[gene.name] = min(max(nv, gene.min), gene.max) if gene.type != "int" else int(min(max(nv, gene.min), gene.max))
        if gene.type == "float":
            out[gene.name] = round(out[gene.name], 4)
    return out


_TESTS: Dict = {}
_PC = PortfolioConfig()
_WF = WFConfig()


def run_task(args):
    """Un algoritmo en un pliegue: búsqueda, meseta y prueba fuera de muestra. Devuelve un dict serializable."""
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    name, fid = args
    wf, pc = _WF, _PC
    train, test = _TESTS[fid]["train"], _TESTS[fid]["test"]
    genes = load_genes(name)
    current = {g.name: getattr(make_algo(name).p, g.name) for g in genes}
    seed = int(wf.seed + zlib.crc32(f"{name}-{fid}".encode()) % 10_000)   # determinista entre ejecuciones
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.enqueue_trial(_enqueue_params(genes, current, wf.radius))
    study.optimize(lambda t: score_train(name, _suggest(t, genes, current, wf.radius), train, pc, wf), n_trials=wf.trials)

    seen, cands = set(), []
    for t in sorted([t for t in study.trials if t.value is not None], key=lambda t: t.value, reverse=True):
        g = _genome_from(t.params, genes, current)
        key = json.dumps(g, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key); cands.append((t.value, g))
        if len(cands) == wf.top_candidates:
            break
    rng = random.Random(seed)
    scored = []
    for own, g in cands:
        nb = [score_train(name, perturb(g, genes, rng, wf.perturbation), train, pc, wf) for _ in range(wf.neighbors)]
        scored.append({"own": own, "neighbors": float(np.mean(nb)), "plateau": float(np.mean([own] + nb)), "genome": g})
    peak = max(scored, key=lambda c: c["own"])
    plateau = max(scored, key=lambda c: c["plateau"])
    variants = {"actual": current, "pico": peak["genome"], "meseta": plateau["genome"]}
    res = {"algorithm": name, "fold": fid, "genes": [g.name for g in genes], "train_actual": study.trials[0].value,
           "pico_train": peak["own"], "meseta_train": plateau["own"], "meseta_neighbors": plateau["neighbors"],
           "pico_neighbors": peak["neighbors"], "genomes": {k: v for k, v in variants.items()}, "oos": {}}
    for k, g in variants.items():
        m, trades, alphas, expo = evaluate(name, g, test, pc)
        res["oos"][k] = {"alpha": alphas, "mean": m, "trades": trades, "exposure": expo}
    return res


# ----------------------------- orquestación -----------------------------
def build_tests(names: List[str], folds: List[dict], wf: WFConfig, pc: PortfolioConfig) -> None:
    global _TESTS
    cfg = load_ga_config()
    cols = {"date", "mkt_irx", *OHLC}
    for n in names:
        cols |= set(make_algo(n).requires)
    with StockDB(cfg.db_path) as db:
        symbols = db.symbols()
        spans = pd.read_sql_query("SELECT symbol, MIN(date) AS first, MAX(date) AS last FROM prices WHERE interval='1d' "
                                  "GROUP BY symbol", db.conn, parse_dates=["first", "last"]).set_index("symbol").loc[symbols]
        calendar = pd.DatetimeIndex(db.load("^GSPC", with_indicators=False)["date"])
        cache = {}
        for s in symbols:
            d = db.load(s, with_indicators=True, with_market=db.has_market())
            cache[s] = d[[c for c in d.columns if c in cols]]
        for f in folds:
            rt = random.Random(f"{wf.seed}-{f['id']}")
            tr = [sample_portfolio_test(spans, calendar, cache.__getitem__, cfg, pc, random.Random(f"{wf.seed}-{f['id']}-tr{k}"),
                                        columns=cols, date_min=f["train"][0], date_max=f["train"][1]) for k in range(wf.train_tests)]
            te = [sample_portfolio_test(spans, calendar, cache.__getitem__, cfg, pc, random.Random(f"{wf.seed}-{f['id']}-te{k}"),
                                        columns=cols, date_min=f["test"][0], date_max=f["test"][1]) for k in range(wf.test_tests)]
            _TESTS[f["id"]] = {"train": tr, "test": te}
    del cache
    gc.collect()


def summarize(results: List[dict]) -> pd.DataFrame:
    rows = []
    for name in sorted({r["algorithm"] for r in results}):
        rs = [r for r in results if r["algorithm"] == name]
        pooled = {k: np.concatenate([r["oos"][k]["alpha"] for r in rs]) for k in ("actual", "pico", "meseta")}
        row = {"algorithm": name, "pliegues": len(rs), "pruebas_oos": len(pooled["actual"])}
        for k, x in pooled.items():
            lo, hi = bootstrap_ci(x, seed=1)
            row[f"alpha_{k}"] = x.mean(); row[f"{k}_ic_inf"] = lo; row[f"{k}_ic_sup"] = hi
        for k in ("pico", "meseta"):
            d = pooled[k] - pooled["actual"]
            lo, hi = bootstrap_ci(d, seed=2)
            row[f"{k}_menos_actual"] = d.mean(); row[f"{k}_menos_actual_ic_inf"] = lo; row[f"{k}_menos_actual_ic_sup"] = hi
            row[f"pliegues_mejoran_{k}"] = int(sum(r["oos"][k]["mean"] > r["oos"]["actual"]["mean"] for r in rs))
        row["train_meseta"] = float(np.mean([r["meseta_train"] for r in rs]))
        row["train_pico"] = float(np.mean([r["pico_train"] for r in rs]))
        row["fragilidad_pico"] = float(np.mean([r["pico_train"] - r["pico_neighbors"] for r in rs]))
        row["fragilidad_meseta"] = float(np.mean([r["meseta_train"] - r["meseta_neighbors"] for r in rs]))
        rows.append(row)
    return pd.DataFrame(rows).set_index("algorithm")


def main():
    global _PC, _WF
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithms", nargs="+")
    ap.add_argument("--stage", choices=["walkforward", "final"], default="walkforward")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--tag", default="")
    ap.add_argument("--apply", default="", metavar="alg1,alg2",
                    help="solo con --stage final: escribe en variables.cfg la 'meseta' de estos algoritmos")
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor", help="sobrescribe walkforward.cfg")
    ap.add_argument("--portfolio", nargs="*", default=[], metavar="clave=valor", help="sobrescribe portfolio.cfg")
    a = ap.parse_args()
    wf = load_wf_config(**{k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)})
    pc = load_portfolio_config(**{k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.portfolio)})
    _PC, _WF = pc, wf
    folds = [final_fold(wf)] if a.stage == "final" else make_folds(wf)
    print(f"{a.stage}: {len(a.algorithms)} algoritmos × {len(folds)} pliegues; entrenamiento {wf.train_years} años, "
          f"prueba {wf.test_years}; {wf.trials} evaluaciones bayesianas por pliegue; carteras de {pc.n_stocks} acciones, "
          f"hasta {pc.max_positions} posiciones")
    for f in folds:
        print(f"  pliegue {f['id']}: entrena {f['train'][0].date()}→{f['train'][1].date()}  prueba {f['test'][0].date()}→"
              f"{'fin de datos' if f['test'][1].year > 2090 else f['test'][1].date()}")
    build_tests(a.algorithms, folds, wf, pc)
    tasks = [(n, f["id"]) for n in a.algorithms for f in folds]
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context("fork")) as ex:
        results = list(ex.map(run_task, tasks))
    out = Path("output"); out.mkdir(exist_ok=True)
    suffix = f"_{a.stage}" + (f"_{a.tag}" if a.tag else "")
    (out / f"walkforward{suffix}.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    if a.apply:
        if a.stage != "final":
            raise SystemExit("--apply solo se usa con --stage final (parámetros reentrenados con los últimos años)")
        from .tune import update_cfg_values
        for r in results:
            if r["algorithm"] in a.apply.split(","):
                update_cfg_values(HERE / r["algorithm"] / "variables.cfg", r["genomes"]["meseta"])
                print(f"variables.cfg de {r['algorithm']} actualizado con la meseta: {r['genomes']['meseta']}")
    s = summarize(results)
    s.round(3).to_csv(out / f"walkforward_summary{suffix}.csv")
    pd.set_option("display.width", 220)
    print("\nAlpha medio FUERA DE MUESTRA (carteras nuevas de la ventana de prueba) con IC 95%:")
    print(s[["pliegues", "pruebas_oos", "alpha_actual", "alpha_pico", "alpha_meseta"]].round(2).to_string())
    print("\nMeseta menos actual (IC 95%) | pliegues que mejoran | alpha de entrenamiento -> fuera de muestra (sobreajuste):")
    print(s[["meseta_menos_actual", "meseta_menos_actual_ic_inf", "meseta_menos_actual_ic_sup", "pliegues_mejoran_meseta",
             "pico_menos_actual", "pliegues_mejoran_pico", "train_pico", "train_meseta", "fragilidad_pico",
             "fragilidad_meseta"]].round(2).to_string())


if __name__ == "__main__":
    main()
