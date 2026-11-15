"""Torneo: todos los algoritmos compiten sobre las MISMAS acciones y periodos.

En cada ronda se sortean `n_symbols` acciones con periodos de `min_bars`..`max_bars`
barras (ver genetic.cfg). Todos los algoritmos (y un benchmark buy&hold) se
evalúan sobre esa muestra con la misma fórmula de fitness del algoritmo genético:
    fitness = CAGR medio% - dd_penalty * |max drawdown| medio%
Ranking final = puesto medio entre rondas (robusto a rondas atípicas con un multiplicador
enorme o a la penalización por pocas operaciones); se informan fitness medio y mediano.

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
from .genetic import PENALTY, GAConfig, load_ga_config, make_algo, sample_windows

HERE = Path(__file__).parent
BENCH = "buy&hold"


def discover_all() -> List[str]:
    return sorted(p.name for p in HERE.glob("algorithm*") if (p / "algorithm.py").exists())


def _score(cagr, dd, n_trades, cfg: GAConfig) -> float:
    if n_trades < cfg.min_trades:
        return PENALTY + n_trades
    return float(np.mean(cagr) - cfg.dd_penalty * np.mean(dd))


def evaluate_round(names: List[str], samples, cfg: GAConfig, use_best: bool) -> pd.DataFrame:
    rows = []
    for name in names:
        best = HERE / name / "best_variables.cfg"
        algo = make_algo(name, cfg=str(best)) if use_best and best.exists() else make_algo(name)
        cagr, dd, rets = [], [], []
        expo = []
        for _, df in samples:
            r = backtest(algo, df)
            cagr.append(r.metrics["CAGR_%"]); dd.append(abs(r.metrics["max_drawdown_%"]))
            expo.append(r.metrics["exposicion_%"])
            if len(r.trades):
                rets.extend(r.trades["return_pct"].tolist())
        rows.append({"algorithm": name, "fitness": _score(cagr, dd, len(rets), cfg),
                     "cagr_%": np.mean(cagr), "max_dd_%": np.mean(dd), "operaciones": len(rets),
                     "aciertos_%": np.mean(np.array(rets) > 0) * 100 if rets else np.nan,
                     "ret_medio_op_%": np.mean(rets) * 100 if rets else np.nan,
                     "exposicion_%": np.mean(expo)})
    # benchmark: comprar al inicio del periodo y mantener
    cagr, dd = [], []
    for _, df in samples:
        c = df["close"].to_numpy(float)
        years = max((df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25, 1e-9)
        cagr.append(((c[-1] / c[0]) ** (1 / years) - 1) * 100)
        dd.append(abs((c / np.maximum.accumulate(c) - 1).min()) * 100)
    rows.append({"algorithm": BENCH, "fitness": float(np.mean(cagr) - cfg.dd_penalty * np.mean(dd)),
                 "cagr_%": np.mean(cagr), "max_dd_%": np.mean(dd), "operaciones": 1,
                 "aciertos_%": np.nan, "ret_medio_op_%": np.nan, "exposicion_%": 100.0})
    return pd.DataFrame(rows)


def compete(cfg: GAConfig, rounds: int = 3, use_best: bool = False, names=None, log=print,
            group: str = "all", period: str = "all", tag: str = "", since=None) -> pd.DataFrame:
    names = names or discover_all()
    seed = cfg.seed if cfg.seed is not None else random.randrange(2**31)
    log(f"Torneo: {len(names)} algoritmos + {BENCH}, {rounds} rondas, "
        f"{cfg.n_symbols} acciones/ronda, periodos {cfg.min_bars}-{cfg.max_bars} barras (seed={seed})")
    per_round: List[pd.DataFrame] = []
    with StockDB(cfg.db_path) as db:
        symbols = db.symbols()
        if group != "all":  # mismo reparto disjunto que algorithms.analyze
            symbols = split_symbols(symbols)[0 if group == "analysis" else 1]
        load = lambda s: db.load(s, with_indicators=True, with_market=db.has_market())
        for k in range(rounds):
            samples = sample_windows(symbols, load, cfg, random.Random(f"{seed}-round{k}"),
                                     date_min=cfg.test_start if period == "test" else since,
                                     date_max=cfg.train_end if period == "train" else None)
            res = evaluate_round(names, samples, cfg, use_best)
            res["round"] = k + 1
            res["rank"] = res["fitness"].rank(ascending=False, method="min").astype(int)
            per_round.append(res)
            log(f"  ronda {k + 1}: ganador {res.sort_values('fitness').iloc[-1]['algorithm']}")
    allr = pd.concat(per_round)
    agg = allr.groupby("algorithm").agg(
        fitness=("fitness", "mean"), fitness_mediana=("fitness", "median"), fitness_std=("fitness", "std"),
        rondas_ganadas=("rank", lambda r: int((r == 1).sum())), rank_medio=("rank", "mean"),
        cagr_pct=("cagr_%", "mean"), max_dd_pct=("max_dd_%", "mean"),
        operaciones=("operaciones", "sum"), aciertos_pct=("aciertos_%", "mean"),
        ret_medio_op_pct=("ret_medio_op_%", "mean"), exposicion_pct=("exposicion_%", "mean"),
    ).sort_values(["rank_medio", "fitness_mediana"], ascending=[True, False])
    agg["calmar"] = agg["cagr_pct"] / agg["max_dd_pct"]   # CAGR / drawdown: no premia quedarse en efectivo
    agg.insert(0, "puesto", range(1, len(agg) + 1))
    out = Path("output"); out.mkdir(exist_ok=True)
    suffix = "".join(f"_{x}" for x in (None if group == "all" else group,
                                       None if period == "all" else period, tag or None) if x)
    agg.round(2).to_csv(out / f"competition{suffix}.csv")
    allr.round(3).to_csv(out / f"competition_rounds{suffix}.csv", index=False)
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
    ap.add_argument("--tag", default="", help="sufijo para los CSV de salida (p.ej. before/after)")
    ap.add_argument("--group", choices=["all", "analysis", "validation"], default="all",
                    help="subconjunto de acciones (analysis/validation son mitades disjuntas)")
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor", help="sobrescribe genetic.cfg")
    a = ap.parse_args()
    over = {k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)}
    if a.seed is not None:
        over["seed"] = a.seed
    cfg = load_ga_config(**over)
    agg = compete(cfg, a.rounds, a.best, a.algorithms or None, group=a.group, period=a.period, tag=a.tag, since=a.since)
    pd.set_option("display.width", 200)
    print("\n" + agg.round(2).to_string())
    print("\nGuardado en output/competition*.csv")


if __name__ == "__main__":
    main()
