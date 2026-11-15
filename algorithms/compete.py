"""Torneo: todos los algoritmos compiten sobre las MISMAS pruebas aleatorias.

Cada ronda sortea `n_symbols` pruebas independientes (acción, fecha de inicio y `min_bars`..`max_bars` jornadas;
ver genetic.cfg). Cada algoritmo (y un benchmark buy&hold) se evalúa en cada prueba con el **alpha de timing**
(ver `algorithms/metrics.py`): CAGR de la estrategia menos el de una cartera con la misma exposición (acción +
efectivo que rinde la letra a 13 semanas). Estar en efectivo da ~0, así que la métrica ya no premia no operar.

Ranking final = alpha medio sobre todas las pruebas, con intervalo de confianza 95% (bootstrap), % de pruebas con
alpha > 0 y p-valor ajustado por múltiples comparaciones (Benjamini-Hochberg). `rank_medio` = puesto medio por ronda.

Uso:  python -m algorithms.compete [--rounds 5] [--group validation] [--period test] [--tag x] [--seed 1] [--best] [--set n_symbols=30]
  --best   usa best_variables.cfg (salida del genético) cuando existe, en vez de variables.cfg
"""
from __future__ import annotations

import argparse
import ast
import random
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from ticker2db import StockDB

from .analyze import split_symbols
from .engine import backtest
from .metrics import summarize_tests
from .genetic import PENALTY, GAConfig, load_ga_config, loader, make_algo, sample_windows

HERE = Path(__file__).parent
BENCH = "buy&hold"


def discover_all() -> List[str]:
    return sorted(p.name for p in HERE.glob("algorithm*") if (p / "algorithm.py").exists())


def _round_fitness(alphas, dds, n_trades, cfg: GAConfig) -> float:
    if n_trades < cfg.min_trades:
        return PENALTY + n_trades
    return float(np.mean(alphas) - cfg.dd_penalty * np.mean(dds))


def evaluate_round(names: List[str], samples, cfg: GAConfig, use_best: bool):
    """Devuelve (resumen por algoritmo de la ronda, una fila por algoritmo y prueba)."""
    rows, tests = [], []
    for name in names:
        best = HERE / name / "best_variables.cfg"
        algo = make_algo(name, cfg=str(best)) if use_best and best.exists() else make_algo(name)
        alphas, dds, cagrs, expo, rets = [], [], [], [], []
        for t, (sym, df) in enumerate(samples):
            r = backtest(algo, df)
            m = r.metrics
            alphas.append(m["alpha_timing_%"]); dds.append(abs(m["max_drawdown_%"])); cagrs.append(m["CAGR_%"])
            expo.append(m["exposicion_%"])
            if len(r.trades):
                rets.extend(r.trades["return_pct"].tolist())
            tests.append({"algorithm": name, "test": t, "symbol": sym, "start": df["date"].iloc[0].date(),
                          "bars": len(df), "alpha": m["alpha_timing_%"], "cagr": m["CAGR_%"],
                          "max_dd": abs(m["max_drawdown_%"]), "exposure": m["exposicion_%"],
                          "trades": m["operaciones"], "bh_cagr": m["bh_CAGR_%"]})
        rows.append({"algorithm": name, "fitness": _round_fitness(alphas, dds, len(rets), cfg),
                     "cagr_%": np.mean(cagrs), "max_dd_%": np.mean(dds), "operaciones": len(rets),
                     "aciertos_%": np.mean(np.array(rets) > 0) * 100 if rets else np.nan,
                     "ret_medio_op_%": np.mean(rets) * 100 if rets else np.nan,
                     "exposicion_%": np.mean(expo)})
    # benchmark: comprar al inicio de cada prueba y mantener (alpha 0 por construcción)
    bh_cagr, bh_dd = [], []
    for t, (sym, df) in enumerate(samples):
        c = df["close"].to_numpy(float)
        years = max((df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25, 1e-9)
        cg = ((c[-1] / c[0]) ** (1 / years) - 1) * 100
        dd = abs((c / np.maximum.accumulate(c) - 1).min()) * 100
        bh_cagr.append(cg); bh_dd.append(dd)
        tests.append({"algorithm": BENCH, "test": t, "symbol": sym, "start": df["date"].iloc[0].date(),
                      "bars": len(df), "alpha": 0.0, "cagr": cg, "max_dd": dd, "exposure": 100.0,
                      "trades": 1, "bh_cagr": cg})
    rows.append({"algorithm": BENCH, "fitness": float(-cfg.dd_penalty * np.mean(bh_dd)),
                 "cagr_%": np.mean(bh_cagr), "max_dd_%": np.mean(bh_dd), "operaciones": 1,
                 "aciertos_%": np.nan, "ret_medio_op_%": np.nan, "exposicion_%": 100.0})
    return pd.DataFrame(rows), pd.DataFrame(tests)


def compete(cfg: GAConfig, rounds: int = 3, use_best: bool = False, names=None, log=print,
            group: str = "all", period: str = "all", tag: str = "", since=None,
            show_samples: int = 0) -> pd.DataFrame:
    names = names or discover_all()
    seed = cfg.seed if cfg.seed is not None else random.randrange(2**31)
    log(f"Torneo: {len(names)} algoritmos + {BENCH}, {rounds} rondas de {cfg.n_symbols} pruebas aleatorias "
        f"(acción, fecha de inicio y {cfg.min_bars}-{cfg.max_bars} jornadas) (seed={seed})")
    limits = [f"{k}={v}" for k, v in (("group", group if group != "all" else None),
              ("period", period if period != "all" else None), ("since", since)) if v]
    if limits:
        log("  RESTRICCIONES al sorteo: " + ", ".join(limits) + "  (el sorteo ya no cubre todo el historial)")
    per_round: List[pd.DataFrame] = []
    all_tests: List[pd.DataFrame] = []
    with StockDB(cfg.db_path) as db:
        symbols = db.symbols()
        if group != "all":  # mismo reparto disjunto que algorithms.analyze
            symbols = split_symbols(symbols)[0 if group == "analysis" else 1]
        load = loader(db, names)
        for k in range(rounds):
            samples = sample_windows(symbols, load, cfg, random.Random(f"{seed}-round{k}"),
                                     date_min=cfg.test_start if period == "test" else since,
                                     date_max=cfg.train_end if period == "train" else None)
            if show_samples and k == 0:
                log("  ejemplo de la ronda 1:")
                for sym, d in samples[:show_samples]:
                    log(f"    {sym:<6} desde {d['date'].iloc[0].date()}  {len(d)} jornadas")
            res, tests = evaluate_round(names, samples, cfg, use_best)
            tests["round"] = k + 1
            all_tests.append(tests)
            res["round"] = k + 1
            res["rank"] = res["fitness"].rank(ascending=False, method="min").astype(int)
            per_round.append(res)
            log(f"  ronda {k + 1}: mejor alpha medio: {res.sort_values('fitness').iloc[-1]['algorithm']}")
    allr = pd.concat(per_round)
    tests_all = pd.concat(all_tests)
    stats = summarize_tests(tests_all, "alpha", seed=seed)
    legacy = allr.groupby("algorithm").agg(
        fitness_mediana=("fitness", "median"), rondas_ganadas=("rank", lambda r: int((r == 1).sum())),
        rank_medio=("rank", "mean"), cagr_pct=("cagr_%", "mean"), max_dd_pct=("max_dd_%", "mean"),
        operaciones=("operaciones", "sum"), aciertos_pct=("aciertos_%", "mean"),
        ret_medio_op_pct=("ret_medio_op_%", "mean"), exposicion_pct=("exposicion_%", "mean"))
    agg = stats.join(legacy).sort_values("alpha_medio", ascending=False)
    agg["calmar"] = agg["cagr_pct"] / agg["max_dd_pct"]
    agg.insert(0, "puesto", range(1, len(agg) + 1))
    out = Path("output"); out.mkdir(exist_ok=True)
    suffix = "".join(f"_{x}" for x in (None if group == "all" else group,
                                       None if period == "all" else period, tag or None) if x)
    agg.round(2).to_csv(out / f"competition{suffix}.csv")
    allr.round(3).to_csv(out / f"competition_rounds{suffix}.csv", index=False)
    tests_all.round(3).to_csv(out / f"competition_tests{suffix}.csv", index=False)   # una fila por algoritmo y prueba
    return agg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithms", nargs="*", help="por defecto, todos")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--best", action="store_true")
    ap.add_argument("--period", choices=["all", "train", "test"], default="all",
                    help="train: periodos hasta train_end; test: periodos desde test_start (genetic.cfg)")
    ap.add_argument("--since", help="los periodos no empiezan antes de esta fecha (p.ej. 1996-01-01: datos de mercado completos)")
    ap.add_argument("--show-samples", type=int, default=0, metavar="N", help="muestra N pruebas de la ronda 1")
    ap.add_argument("--tag", default="", help="sufijo para los CSV de salida (p.ej. before/after)")
    ap.add_argument("--group", choices=["all", "analysis", "validation"], default="all",
                    help="subconjunto de acciones (analysis/validation son mitades disjuntas)")
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor", help="sobrescribe genetic.cfg")
    a = ap.parse_args()
    over = {k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)}
    if a.seed is not None:
        over["seed"] = a.seed
    cfg = load_ga_config(**over)
    agg = compete(cfg, a.rounds, a.best, a.algorithms or None, group=a.group, period=a.period, tag=a.tag, since=a.since, show_samples=a.show_samples)
    pd.set_option("display.width", 200)
    cols = ["puesto", "alpha_medio", "alpha_ic_inf", "alpha_ic_sup", "pct_alpha_pos", "p_ajustado", "significativo",
            "cagr_pct", "max_dd_pct", "exposicion_pct", "operaciones", "calmar", "rank_medio"]
    print("\n" + agg[cols].round(2).to_string())
    print(f"\nalpha = puntos de CAGR sobre una cartera con la misma exposición (efectivo a la letra de 13 sem.). "
          f"Significativos (FDR 5%, alpha medio > 0): {int(agg['significativo'].sum())} de {len(agg) - 1}")
    print("\nGuardado en output/competition*.csv")


if __name__ == "__main__":
    main()
