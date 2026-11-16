"""Señales de compra para la PRÓXIMA apertura, evaluando todo el S&P 500 con los mejores algoritmos.

Las señales se calculan con los datos hasta el último cierre disponible; se ejecutarían comprando a la apertura de la
siguiente jornada, como en el backtest. Acciones que no están en la base principal se descargan (solo ~5 años de
historial, suficiente para los indicadores) a una base auxiliar `data/sp500_extra.db`, sin tocar el universo de pruebas.

Uso:  python -m algorithms.signals [algoritmos...] [--refresh] [--tag 2026-11-16]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from ticker2db import StockDB, get_sp500_weights, update_symbols

from .genetic import make_algo

BEST = ["algorithm01b_i2", "algorithm03a_v2_r2_i2", "algorithm03a_v1_i2"]   # alpha significativo en 1990-2019 y 2020-2023
EXTRA_DB = "data/sp500_extra.db"
MAIN_DB = "data/stocks.db"


def refresh_missing(symbols: List[str], start: str = "2021-01-01", log=print) -> Dict[str, str]:
    """Descarga a `EXTRA_DB` las acciones que no están en la base principal (ni ya en la auxiliar, salvo actualizar)."""
    with StockDB(MAIN_DB) as db:
        have = set(db.symbols())
    todo = [s for s in symbols if s not in have]
    failed = {}
    t0 = time.time()
    for i, s in enumerate(todo, 1):
        try:
            update_symbols([s], EXTRA_DB, start=start, return_data=False)
        except Exception as e:
            failed[s] = f"{type(e).__name__}: {e}"
        if i % 25 == 0:
            log(f"  descargadas {i}/{len(todo)} ({time.time() - t0:.0f} s)")
    return failed


def load_frames(symbols: List[str], tail: int = 700) -> Dict[str, pd.DataFrame]:
    """DataFrames (precios + indicadores + `mkt_*`) de cada símbolo, desde la base principal o la auxiliar."""
    out: Dict[str, pd.DataFrame] = {}
    with StockDB(MAIN_DB) as main:
        mf = main.market_features()
        have_main = set(main.symbols())
        extra_path = Path(EXTRA_DB)
        extra = StockDB(EXTRA_DB) if extra_path.exists() else None
        have_extra = set(extra.symbols()) if extra else set()
        for s in symbols:
            db = main if s in have_main else (extra if s in have_extra else None)
            if db is None:
                continue
            df = db.load(s, with_indicators=True).tail(tail).reset_index(drop=True)
            if mf is not None and not mf.empty:
                idx = mf.index.union(pd.DatetimeIndex(df["date"].unique()))
                al = mf.reindex(idx).ffill(limit=5).reindex(pd.DatetimeIndex(df["date"]))
                al.index = df.index
                df = pd.concat([df, al], axis=1)
            out[s] = df
        if extra:
            extra.close()
    return out


def evaluate(names: List[str], frames: Dict[str, pd.DataFrame], last_date: pd.Timestamp) -> pd.DataFrame:
    """Una fila por (acción, algoritmo) con señal de compra en la última jornada."""
    rows = []
    for name in names:
        algo = make_algo(name)
        for sym, df in frames.items():
            if df["date"].iloc[-1] != last_date or len(df) < 300:
                continue
            try:
                buy = bool(algo.buy_signal(df).iloc[-1])
            except Exception:
                continue
            if not buy:
                continue
            tp, sp, sz = algo.target_series(df), algo.stop_series(df), algo.size_series(df)
            p = algo.p
            t = tp.iloc[-1] if tp is not None and not np.isnan(tp.iloc[-1]) else p.target_pct
            st = sp.iloc[-1] if sp is not None and not np.isnan(sp.iloc[-1]) else p.stop_pct
            m = sz.iloc[-1] if sz is not None and not np.isnan(sz.iloc[-1]) else 1.0
            last = df.iloc[-1]
            rows.append({"symbol": sym, "algorithm": name, "close": last["close"], "rsi_14": last.get("rsi_14"),
                         "ret5_pct": (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100,
                         "atr_pct": last["atr_14"] / last["close"] * 100, "size_mult": float(m),
                         "target_pct": None if t is None else float(t) * 100,
                         "stop_pct": None if st is None else float(st) * 100, "max_hold_days": p.max_hold_days})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("algorithms", nargs="*", default=BEST)
    ap.add_argument("--refresh", action="store_true", help="descarga las acciones faltantes del S&P 500")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    sp = get_sp500_weights()
    syms = sp["yf_symbol"].tolist()
    if a.refresh:
        failed = refresh_missing(syms)
        print("fallidas:", failed or "ninguna")
    frames = load_frames(syms)
    last = max(df["date"].iloc[-1] for df in frames.values())
    sig = evaluate(a.algorithms, frames, last)
    sig = sig.merge(sp[["yf_symbol", "company", "weight"]].rename(columns={"yf_symbol": "symbol"}), on="symbol", how="left")
    out = Path("output"); out.mkdir(exist_ok=True)
    sig.round(3).to_csv(out / f"signals_{a.tag or str(last.date())}.csv", index=False)
    print(f"{len(frames)}/{len(syms)} acciones evaluadas; último cierre {last.date()}; {len(sig)} señales")
    print(sig.groupby("algorithm").symbol.nunique().to_string())


if __name__ == "__main__":
    main()
