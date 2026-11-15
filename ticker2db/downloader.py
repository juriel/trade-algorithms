"""Descarga de precios OHLCV con yfinance."""
from __future__ import annotations

from typing import Iterable, Optional, Union

import pandas as pd
import yfinance as yf

COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


def download_prices(
    symbols: Union[str, Iterable[str]],
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
    period: Optional[str] = None,
) -> pd.DataFrame:
    """Descarga OHLCV y devuelve un DataFrame en formato largo.

    Columnas: symbol, date, open, high, low, close, adj_close, volume.
    `close` es el precio ajustado por splits (no por dividendos) y `adj_close`
    el ajustado también por dividendos. Si se indica `period` (p.ej. "max",
    "5y") se ignoran start/end.
    """
    if isinstance(symbols, str):
        symbols = [symbols]
    symbols = list(dict.fromkeys(s.upper() for s in symbols))
    if not symbols:
        return pd.DataFrame(columns=["symbol", "date"] + COLUMNS)

    kwargs = dict(interval=interval, auto_adjust=False, actions=False,
                  group_by="ticker", progress=False, threads=True)
    if period:
        kwargs["period"] = period
    else:
        kwargs.update(start=start, end=end)
    raw = yf.download(symbols, **kwargs)

    frames = []
    for sym in symbols:
        if isinstance(raw.columns, pd.MultiIndex):
            if sym not in raw.columns.get_level_values(0):
                continue
            df = raw[sym].copy()
        else:  # un solo símbolo en algunas versiones
            df = raw.copy()
        df = df.dropna(how="all")
        if df.empty:
            continue
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df = df.reindex(columns=COLUMNS)
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index.name = "date"
        df.insert(0, "symbol", sym)
        frames.append(df.reset_index())

    if not frames:
        return pd.DataFrame(columns=["symbol", "date"] + COLUMNS)
    return pd.concat(frames, ignore_index=True)
