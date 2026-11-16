"""Análisis de operaciones de un algoritmo: de qué salen sus ganancias y pérdidas.

Corre el algoritmo sobre el historial completo de un conjunto de acciones y reúne todas
las operaciones junto con los indicadores del día de la señal (ayer respecto a la entrada).
Para evitar sobreajuste, el análisis usa un grupo de acciones y la validación OTRO
grupo disjunto (`split`).

Uso:  python -m algorithms.analyze algorithm03c [--group analysis|validation]
"""
from __future__ import annotations

import argparse
import random
from typing import List, Tuple

import numpy as np
import pandas as pd

from ticker2db import StockDB

from .engine import backtest
from .genetic import load_ga_config, loader, make_algo

EXTRA = ["vol_ratio3", "vol_dryup", "cmf20", "obv_flow20", "vol_ratio", "ret5", "ret20", "dist_high252", "ibs", "gap_pct", "range_pct", "dow", "cdl_net"]
FEATURES = ["rsi_14", "stoch_k", "adx_14", "cci_14", "mfi_14", "atr_pct", "dist_sma20",
            "dist_sma50", "dist_sma200", "slope_sma200", "bb_width", "bb_pos", "macd_hist_pct"]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["atr_pct"] = d["atr_14"] / d["close"] * 100
    for n in (20, 50, 200):
        d[f"dist_sma{n}"] = (d["close"] / d[f"sma_{n}"] - 1) * 100
    d["slope_sma200"] = (d["sma_200"] / d["sma_200"].shift(20) - 1) * 100
    d["bb_width"] = (d["bb_upper"] - d["bb_lower"]) / d["bb_middle"] * 100
    d["bb_pos"] = (d["close"] - d["bb_lower"]) / (d["bb_upper"] - d["bb_lower"])
    d["macd_hist_pct"] = d["macd_hist"] / d["close"] * 100
    # variables de la jornada de la señal (todas se conocen al cierre)
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    d["vol_ratio"] = d["volume"] / d["volume"].rolling(20).mean().shift(1).replace(0, np.nan)
    d["vol_ratio3"] = d["volume"].rolling(3).mean() / d["volume"].rolling(20).mean().shift(3).replace(0, np.nan)
    d["vol_dryup"] = d["volume"].rolling(5).mean() / d["volume"].shift(5).rolling(20).mean().replace(0, np.nan)
    _rng = (d["high"] - d["low"]).replace(0, np.nan)
    _mfv = ((d["close"] - d["low"]) - (d["high"] - d["close"])) / _rng * d["volume"]
    d["cmf20"] = _mfv.rolling(20).sum() / d["volume"].rolling(20).sum().replace(0, np.nan)
    _obv = (np.sign(d["close"].diff().fillna(0)) * d["volume"]).cumsum()
    d["obv_flow20"] = (_obv - _obv.shift(20)) / d["volume"].rolling(20).sum().replace(0, np.nan)
    d["ret5"] = d["close"].pct_change(5) * 100
    d["ret20"] = d["close"].pct_change(20) * 100
    d["dist_high252"] = (d["close"] / d["close"].rolling(252, min_periods=60).max() - 1) * 100
    d["ibs"] = (d["close"] - d["low"]) / rng
    d["gap_pct"] = (d["open"] / d["close"].shift(1) - 1) * 100
    d["range_pct"] = rng / d["close"] * 100
    d["dow"] = pd.to_datetime(d["date"]).dt.dayofweek
    cdl = [c for c in d.columns if c.startswith("cdl_") and c not in ("cdl_net",)]
    neutral = {"cdl_doji", "cdl_longleggeddoji", "cdl_rickshawman", "cdl_dragonflydoji", "cdl_gravestonedoji", "cdl_takuri"}
    cdl = [c for c in cdl if c not in neutral]
    d["cdl_net"] = ((d[cdl] > 0).sum(axis=1) - (d[cdl] < 0).sum(axis=1)) if cdl else 0
    return d


def split_symbols(symbols: List[str], seed: int = 11) -> Tuple[List[str], List[str]]:
    s = sorted(symbols)
    random.Random(seed).shuffle(s)
    half = len(s) // 2
    return s[:half], s[half:]


def collect_trades(name: str, symbols: List[str], db_path: str, warmup: int = 200,
                   cfg_file=None, since=None, until=None) -> pd.DataFrame:
    """Operaciones de `name` con los indicadores de ayer (y las `mkt_*` si la BD las tiene).
    `since`/`until` filtran por fecha de entrada."""
    algo = make_algo(name, cfg=cfg_file) if cfg_file else make_algo(name)
    out = []
    with StockDB(db_path) as db:
        load = lambda s: db.load(s, with_indicators=True, with_market=db.has_market(), with_candles=db.has_candles())
        for sym in symbols:
            df = load(sym).sort_values("date").reset_index(drop=True)
            if len(df) < warmup + 100:
                continue
            df = df.iloc[warmup:].reset_index(drop=True)
            r = backtest(algo, df)
            if r.trades.empty:
                continue
            mkt = [c for c in df.columns if c.startswith("mkt_")]
            prev = add_features(df).shift(1)[["date"] + FEATURES + EXTRA + mkt].rename(columns={"date": "signal_date"})
            prev["entry_date"] = df["date"]
            t = r.trades.merge(prev, on="entry_date", how="left")
            t["symbol"] = sym
            if since is not None:
                t = t[t["entry_date"] >= pd.Timestamp(since)]
            if until is not None:
                t = t[t["entry_date"] <= pd.Timestamp(until)]
            out.append(t)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def summarize(t: pd.DataFrame) -> dict:
    w, l = t[t.return_pct > 0].return_pct, t[t.return_pct <= 0].return_pct
    return {"operaciones": len(t), "aciertos_%": round(float((t.return_pct > 0).mean()) * 100, 1),
            "ret_medio_%": round(float(t.return_pct.mean()) * 100, 2),
            "ganancia_media_%": round(float(w.mean()) * 100, 2), "perdida_media_%": round(float(l.mean()) * 100, 2),
            "peor_op_%": round(float(t.return_pct.min()) * 100, 1),
            "dias_medios": round(float(t.days_held.mean()), 1),
            "profit_factor": round(float(w.sum() / abs(l.sum())), 2) if len(l) and l.sum() else None}


def report(name: str, t: pd.DataFrame, bins: int = 4) -> str:
    L = [f"### {name}", "", str(summarize(t)), "", "Por motivo de salida:"]
    g = t.groupby("reason").agg(n=("return_pct", "size"), ret_medio=("return_pct", lambda s: s.mean() * 100),
                                dias=("days_held", "mean"))
    L.append(g.round(2).to_string()); L += ["", "Por quinquenio de entrada (retorno medio %, n):"]
    yr = pd.to_datetime(t.entry_date).dt.year
    y = t.groupby((yr // 5) * 5).return_pct.agg(["mean", "size"])
    y["mean"] *= 100
    y.index = [f"{i}-{i + 4}" for i in y.index]
    L.append(y.round(2).T.to_string()); L += ["", f"Retorno medio % por cuartil de cada indicador (de ayer):"]
    for f in [c for c in t.columns if c in FEATURES or c in EXTRA or c.startswith("mkt_")]:
        s = t[[f, "return_pct"]].dropna()
        if s[f].nunique() < bins:
            continue
        q = pd.qcut(s[f], bins, duplicates="drop")
        r = s.groupby(q, observed=True).return_pct.agg(["mean", "size"])
        L.append(f"{f:<14}" + "  ".join(f"[{i.left:.2f},{i.right:.2f}] {row['mean']*100:5.2f}% (n={int(row['size'])})"
                                      for i, row in r.iterrows()))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("algorithm")
    ap.add_argument("--group", choices=["analysis", "validation", "all"], default="analysis")
    ap.add_argument("--since", help="solo operaciones con entrada desde esta fecha")
    ap.add_argument("--until", help="solo operaciones con entrada hasta esta fecha")
    a = ap.parse_args()
    cfg = load_ga_config()
    with StockDB(cfg.db_path) as db:
        syms = db.symbols()
    an, va = split_symbols(syms)
    chosen = {"analysis": an, "validation": va, "all": syms}[a.group]
    print(report(a.algorithm, collect_trades(a.algorithm, chosen, cfg.db_path, since=a.since, until=a.until)))


if __name__ == "__main__":
    main()
