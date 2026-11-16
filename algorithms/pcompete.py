"""Torneo de CARTERAS: todos los algoritmos compiten en las MISMAS pruebas.

Cada prueba sortea un periodo (inicio y largo de 300-600 jornadas al azar) y 20 acciones al azar con datos en ese
periodo (ver portfolio.cfg y genetic.cfg). Cada algoritmo opera esa cartera con capital compartido
(`algorithms/portfolio.py`). Métrica: alpha de timing frente a las mismas acciones a partes iguales comprar y
mantener (con la misma exposición), con IC 95% (bootstrap) y p-valor ajustado por múltiples comparaciones.

Uso:  python -m algorithms.pcompete [algoritmos...] [--tests 100] [--workers 6] [--seed 2026] [--tag x] [--set max_positions=5]
"""
from __future__ import annotations

import argparse
import ast
import gc
import multiprocessing as mp
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from ticker2db import StockDB

from .compete import BENCH, discover_all
from .engine import OHLC
from .genetic import load_ga_config, make_algo, needs_candles
from .metrics import summarize_tests
from .portfolio import (PortfolioConfig, backtest_portfolio, load_portfolio_config, sample_portfolio_test)

_TESTS: list = []   # se rellena antes de crear los procesos (fork: se comparte sin copiar)
_PC: PortfolioConfig = PortfolioConfig()


def _eval_algo(name: str) -> List[dict]:
    algo = make_algo(name)
    rows = []
    for k, (syms, frames, sb) in enumerate(_TESTS):
        m = backtest_portfolio(algo, frames, sb, _PC.max_positions, _PC.initial_capital, seed=k).metrics
        rows.append({"algorithm": name, "test": k, "alpha": m["alpha_timing_%"], "cagr": m["CAGR_%"],
                     "bh_cagr": m["bh_CAGR_%"], "excess": m["CAGR_%"] - m["bh_CAGR_%"], "max_dd": abs(m["max_drawdown_%"]),
                     "bh_dd": abs(m["bh_max_drawdown_%"]), "sharpe": m["sharpe"], "exposure": m["exposicion_%"],
                     "trades": m["operaciones"], "win": m["aciertos_%"]})
    return rows


def pcompete(names: List[str], n_tests: int, seed: int, workers: int, pc: PortfolioConfig, tag: str = "",
             log=print) -> pd.DataFrame:
    global _TESTS, _PC
    _PC = pc
    cfg = load_ga_config()
    log(f"Torneo de carteras: {len(names)} algoritmos + {BENCH}, {n_tests} pruebas de {pc.n_stocks} acciones "
        f"({cfg.min_bars}-{cfg.max_bars} jornadas), hasta {pc.max_positions} posiciones, seed={seed}")
    cols = {"date", "mkt_irx", *OHLC}
    for n in names:
        cols |= set(make_algo(n).requires)
    with StockDB(cfg.db_path) as db:
        symbols = db.symbols()
        spans = pd.read_sql_query("SELECT symbol, MIN(date) AS first, MAX(date) AS last FROM prices WHERE interval='1d' "
                                  "GROUP BY symbol", db.conn, parse_dates=["first", "last"]).set_index("symbol").loc[symbols]
        calendar = pd.DatetimeIndex(db.load("^GSPC", with_indicators=False)["date"])
        with_cdl = needs_candles(names) and db.has_candles()
        cache = {}
        for s in symbols:     # una sola lectura por acción, solo con las columnas necesarias
            d = db.load(s, with_indicators=True, with_market=db.has_market(), with_candles=with_cdl)
            cache[s] = d[[c for c in d.columns if c in cols]]
        tests = [sample_portfolio_test(spans, calendar, cache.__getitem__, cfg, pc, random.Random(f"{seed}-p{k}"),
                                       columns=cols) for k in range(n_tests)]
    del cache
    gc.collect()
    starts = [f[s[0]]["date"].iloc[sb] for s, f, sb in tests]
    log(f"  pruebas sorteadas: inicios entre {min(starts).date()} y {max(starts).date()} "
        f"({len({d.year for d in starts})} años distintos)")
    _TESTS = tests
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as ex:
        rows = [r for part in ex.map(_eval_algo, names) for r in part]
    # benchmark: las mismas acciones a partes iguales (alpha 0 por construcción)
    for k, (syms, frames, sb) in enumerate(tests):
        m = backtest_portfolio(make_algo(names[0]), {s: frames[s] for s in syms}, sb, 0, pc.initial_capital).metrics
        rows.append({"algorithm": BENCH, "test": k, "alpha": 0.0, "cagr": m["bh_CAGR_%"], "bh_cagr": m["bh_CAGR_%"],
                     "excess": 0.0, "max_dd": abs(m["bh_max_drawdown_%"]), "bh_dd": abs(m["bh_max_drawdown_%"]),
                     "sharpe": np.nan, "exposure": 100.0, "trades": 0, "win": np.nan})
    t = pd.DataFrame(rows)
    stats = summarize_tests(t, "alpha", seed=seed)
    exc = summarize_tests(t, "excess", seed=seed)[["alpha_medio", "alpha_ic_inf", "alpha_ic_sup"]]
    exc.columns = ["exceso_vs_bh", "exceso_ic_inf", "exceso_ic_sup"]
    agg = t.groupby("algorithm").agg(cagr_pct=("cagr", "mean"), bh_cagr_pct=("bh_cagr", "mean"),
                                     max_dd_pct=("max_dd", "mean"), bh_dd_pct=("bh_dd", "mean"),
                                     exposicion_pct=("exposure", "mean"), operaciones=("trades", "sum"),
                                     sharpe=("sharpe", "mean"))
    out = stats.join(exc).join(agg).sort_values("alpha_medio", ascending=False)
    out["calmar"] = out["cagr_pct"] / out["max_dd_pct"]
    out.insert(0, "puesto", range(1, len(out) + 1))
    d = Path("output"); d.mkdir(exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    out.round(3).to_csv(d / f"portfolio_competition{suffix}.csv")
    t.round(3).to_csv(d / f"portfolio_tests{suffix}.csv", index=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithms", nargs="*", help="por defecto, todos")
    ap.add_argument("--tests", type=int, default=100)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--tag", default="")
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor", help="sobrescribe portfolio.cfg")
    a = ap.parse_args()
    pc = load_portfolio_config(**{k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)})
    out = pcompete(a.algorithms or discover_all(), a.tests, a.seed, a.workers, pc, a.tag)
    pd.set_option("display.width", 230)
    cols = ["puesto", "alpha_medio", "alpha_ic_inf", "alpha_ic_sup", "p_ajustado", "significativo", "exceso_vs_bh",
            "cagr_pct", "bh_cagr_pct", "max_dd_pct", "exposicion_pct", "calmar"]
    print("\n" + out[cols].round(2).head(25).to_string())
    print(f"\nSignificativos (FDR 5%, alpha > 0): {int(out['significativo'].sum())} de {len(out) - 1}. "
          f"Guardado en output/portfolio_competition*.csv")


if __name__ == "__main__":
    main()
