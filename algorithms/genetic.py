"""Algoritmo genético que optimiza las variables de cada algoritmo.

Para CADA algoritmo:
  1. Sortea `n_symbols` acciones de la base de datos y, para cada una, un periodo
     aleatorio de `min_bars`..`max_bars` barras. La muestra es fija durante toda
     la evolución (así los fitness son comparables entre generaciones).
  2. Evoluciona los genes definidos en `algorithmNN/genes.cfg` (selección por
     torneo, cruce uniforme, mutación, elitismo). El individuo inicial 0 son las
     variables actuales de `variables.cfg`, así nunca se parte peor que eso.
  3. Fitness = CAGR medio% - dd_penalty * |max drawdown| medio%, sobre toda la muestra.
  4. Valida el mejor individuo en otra muestra distinta (fuera de muestra) y escribe
     `algorithmNN/best_variables.cfg` (sin tocar `variables.cfg`).

Uso:  python -m algorithms.genetic [algorithm01 ...] [--set population=40 seed=1]
"""
from __future__ import annotations

import argparse
import ast
import configparser
import copy
import importlib
import json
import random
import time
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ticker2db import StockDB

from .engine import backtest, load_cfg

HERE = Path(__file__).parent
PENALTY = -1000.0


@dataclass
class GAConfig:
    n_symbols: int = 50
    min_bars: int = 300
    max_bars: int = 600
    warmup_bars: int = 200
    population: int = 30
    generations: int = 20
    elite: int = 2
    tournament: int = 3
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2
    seed: Optional[int] = None
    dd_penalty: float = 0.5
    min_trades: int = 30
    validate: bool = True
    db_path: str = "data/stocks.db"
    # --- afinado (algorithms.tune) ---
    train_end: str = "2019-12-31"    # entrenamiento y selección solo con periodos hasta esta fecha
    test_start: str = "2020-01-01"   # el torneo final ("--period test") solo usa periodos desde aquí
    train_samples: int = 60          # acciones/periodos de entrenamiento del genético
    select_rounds: int = 10          # rondas de selección (candidato vs. variables actuales)


def load_ga_config(path=HERE / "genetic.cfg", **overrides) -> GAConfig:
    values = load_cfg(path, "ga") if Path(path).exists() else {}
    values.update(overrides)
    return GAConfig(**values)


# ----------------------------- genes ---------------------------------------
@dataclass
class Gene:
    name: str
    type: str                 # float | int | bool
    min: float = 0.0
    max: float = 0.0
    allow_none: bool = False

    def random(self, rng: random.Random):
        if self.allow_none and rng.random() < 0.2:
            return None
        if self.type == "bool":
            return rng.random() < 0.5
        v = rng.uniform(self.min, self.max)
        return int(round(v)) if self.type == "int" else round(v, 4)

    def mutate(self, v, rng: random.Random):
        if self.allow_none and rng.random() < 0.1:
            return None if v is not None else self.random(rng)
        if v is None:
            return self.random(rng)
        if self.type == "bool":
            return not v
        v = v + rng.gauss(0, 0.15 * (self.max - self.min))
        v = min(max(v, self.min), self.max)
        return int(round(v)) if self.type == "int" else round(v, 4)


def load_genes(name: str) -> List[Gene]:
    """Genes del algoritmo: `algorithmNN/genes.cfg` si existe; si no, las variables de su
    dataclass que tengan rango en `gene_ranges.cfg` (rangos centrales por nombre de variable)."""
    cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=("#", ";"))
    cp.optionxform = str
    own = HERE / name / "genes.cfg"
    if own.exists():
        cp.read(own, encoding="utf-8")
    else:
        central = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=("#", ";"))
        central.optionxform = str
        central.read(HERE / "gene_ranges.cfg", encoding="utf-8")
        names = {f.name for f in fields(make_algo(name).p)}
        for sec in central.sections():
            if sec in names:
                cp[sec] = central[sec]
    genes = []
    for sec in cp.sections():
        d = {k: ast.literal_eval(v) if k != "type" else v for k, v in cp[sec].items()}
        genes.append(Gene(sec, d["type"], d.get("min", 0), d.get("max", 0), bool(d.get("allow_none", False))))
    if not genes:
        raise SystemExit(f"{name}/genes.cfg no define ningún gen")
    return genes


# ----------------------------- muestreo ------------------------------------
Sample = Tuple[str, pd.DataFrame]


def sample_windows(symbols: List[str], load: Callable[[str], pd.DataFrame],
                   cfg: GAConfig, rng: random.Random, date_min=None, date_max=None,
                   n: Optional[int] = None) -> List[Sample]:
    """`n` (por defecto `n_symbols`) acciones al azar, cada una con un periodo de
    min_bars..max_bars barras, opcionalmente contenido en [date_min, date_max]."""
    n = n or cfg.n_symbols
    pool = list(symbols)
    rng.shuffle(pool)
    out: List[Sample] = []
    for sym in pool:
        if len(out) == n:
            break
        df = load(sym).sort_values("date").reset_index(drop=True)
        lo, hi = cfg.warmup_bars, len(df)
        if date_min is not None:
            lo = max(lo, int(df["date"].searchsorted(pd.Timestamp(date_min))))
        if date_max is not None:
            hi = min(hi, int(df["date"].searchsorted(pd.Timestamp(date_max), side="right")))
        length = rng.randint(cfg.min_bars, cfg.max_bars)
        last_start = hi - length
        if last_start < lo:
            continue  # historia insuficiente
        start = rng.randint(lo, last_start)
        out.append((sym, df.iloc[start:start + length].reset_index(drop=True)))
    if len(out) < n:
        print(f"  aviso: solo hay {len(out)} símbolos con historia suficiente (pedidos {n})")
    return out


# ----------------------------- fitness -------------------------------------
def make_algo(name: str, **genome):
    return importlib.import_module(f"algorithms.{name}").Algorithm(**genome)


def needs_candles(names) -> bool:
    """¿Alguno de los algoritmos usa columnas de patrones de velas (`cdl_*`) en `requires`?"""
    return any(c.startswith("cdl_") for n in names for c in make_algo(n).requires)


def loader(db, names=()):
    """Función símbolo -> DataFrame con precios, indicadores, `mkt_*` (si hay) y `cdl_*` (solo si algún
    algoritmo de `names` los necesita y la BD los tiene)."""
    cdl = needs_candles(names) and db.has_candles()
    return lambda s: db.load(s, with_indicators=True, with_market=db.has_market(), with_candles=cdl)


def fitness(name: str, genome: dict, samples: List[Sample], cfg: GAConfig) -> float:
    algo = make_algo(name, **genome)
    cagr, dd, trades = [], [], 0
    for _, df in samples:
        m = backtest(algo, df).metrics
        cagr.append(m["CAGR_%"]); dd.append(abs(m["max_drawdown_%"])); trades += m["operaciones"]
    if trades < cfg.min_trades * len(samples) / cfg.n_symbols:   # mínimo proporcional al tamaño de la muestra
        return PENALTY + trades
    return float(np.mean(cagr) - cfg.dd_penalty * np.mean(dd))


# ----------------------------- evolución -----------------------------------
def crossover(a: dict, b: dict, rng: random.Random) -> dict:
    return {k: (a[k] if rng.random() < 0.5 else b[k]) for k in a}


def mutate(g: dict, genes: List[Gene], rate: float, rng: random.Random) -> dict:
    return {gene.name: gene.mutate(g[gene.name], rng) if rng.random() < rate else g[gene.name]
            for gene in genes}


def evolve(name: str, samples: List[Sample], cfg: GAConfig, rng: random.Random,
           log: Callable[[str], None] = print):
    genes = load_genes(name)
    base = make_algo(name).p
    seed_genome = {g.name: getattr(base, g.name) for g in genes}  # variables.cfg actual
    pop = [seed_genome] + [{g.name: g.random(rng) for g in genes} for _ in range(cfg.population - 1)]
    cache: Dict[tuple, float] = {}

    def score(g):
        key = tuple(sorted(g.items(), key=lambda kv: kv[0]))
        if key not in cache:
            cache[key] = fitness(name, g, samples, cfg)
        return cache[key]

    def select(scored):
        return max(rng.sample(scored, min(cfg.tournament, len(scored))), key=lambda t: t[0])[1]

    history = []
    for gen in range(cfg.generations + 1):
        scored = sorted(((score(g), g) for g in pop), key=lambda t: t[0], reverse=True)
        fits = [f for f, _ in scored]
        history.append({"gen": gen, "best": fits[0], "mean": float(np.mean(fits))})
        log(f"  gen {gen:>3}  mejor={fits[0]:8.2f}  media={np.mean(fits):8.2f}  {scored[0][1]}")
        if gen == cfg.generations:
            break
        nxt = [copy.deepcopy(g) for _, g in scored[:cfg.elite]]
        while len(nxt) < cfg.population:
            a, b = select(scored), select(scored)
            child = crossover(a, b, rng) if rng.random() < cfg.crossover_rate else dict(a)
            nxt.append(mutate(child, genes, cfg.mutation_rate, rng))
        pop = nxt
    best_fit, best = scored[0]
    return best, best_fit, seed_genome, score(seed_genome), history


# ----------------------------- ejecución -----------------------------------
def write_best_cfg(name: str, genome: dict, info: dict):
    p = make_algo(name, **genome).p
    lines = ["[params]"] + [f"# {k}: {v}" for k, v in info.items()]
    lines += [f"{f.name} = {getattr(p, f.name)}" for f in fields(p)]
    path = HERE / name / "best_variables.cfg"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def optimize(name: str, cfg: GAConfig, log: Callable[[str], None] = print) -> dict:
    seed = cfg.seed if cfg.seed is not None else random.randrange(2**31)
    rng = random.Random(f"{seed}-{name}")  # muestra distinta por algoritmo
    t0 = time.time()
    with StockDB(cfg.db_path) as db:
        symbols = db.symbols()
        load = loader(db, [name])
        train = sample_windows(symbols, load, cfg, rng)
        valid = sample_windows(symbols, load, cfg, rng) if cfg.validate else []
    log(f"\n=== {name}: {len(train)} acciones, periodos de "
        f"{min(len(d) for _, d in train)}-{max(len(d) for _, d in train)} barras (seed={seed}) ===")
    best, best_fit, base, base_fit, hist = evolve(name, train, cfg, rng, log)
    result = {"algorithm": name, "seed": seed, "best": best, "fitness_train": best_fit,
              "default": base, "fitness_train_default": base_fit, "history": hist}
    if valid:
        result["fitness_valid"] = fitness(name, best, valid, cfg)
        result["fitness_valid_default"] = fitness(name, base, valid, cfg)
    result["train_symbols"] = [s for s, _ in train]
    result["seconds"] = round(time.time() - t0, 1)
    info = {"generado por": "algorithms.genetic", "seed": seed,
            "fitness_train": round(best_fit, 2), "fitness_train_con_variables.cfg": round(base_fit, 2)}
    if valid:
        info["fitness_validacion"] = round(result["fitness_valid"], 2)
        info["fitness_validacion_con_variables.cfg"] = round(result["fitness_valid_default"], 2)
    result["cfg_path"] = str(write_best_cfg(name, best, info))
    log(f"\n  mejor: {best}\n  fitness entrenamiento: {best_fit:.2f} (variables.cfg: {base_fit:.2f})")
    if valid:
        log(f"  fitness validación   : {result['fitness_valid']:.2f} (variables.cfg: {result['fitness_valid_default']:.2f})")
    log(f"  guardado en {result['cfg_path']}  [{result['seconds']} s]")
    return result


def discover() -> List[str]:
    return sorted(p.name for p in HERE.glob("algorithm*") if (p / "genes.cfg").exists())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithms", nargs="*", help="por defecto, todos los que tengan genes.cfg")
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor", help="sobrescribe genetic.cfg")
    a = ap.parse_args()
    cfg = load_ga_config(**{k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)})
    results = [optimize(n, cfg) for n in (a.algorithms or discover())]
    out = Path("output"); out.mkdir(exist_ok=True)
    (out / "ga_results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("\nResultados completos en output/ga_results.json")


if __name__ == "__main__":
    main()
