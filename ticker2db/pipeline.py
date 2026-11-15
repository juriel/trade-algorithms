"""Pipeline completo: descarga -> indicadores -> SQLite (incremental)."""
from __future__ import annotations

from typing import Iterable, List, Optional, Union

import pandas as pd

from .downloader import download_prices
from .indicators import IndicatorSpec, add_indicators
from .storage import StockDB

# Barras previas necesarias para que los indicadores largos (SMA 200...) converjan.
WARMUP_BARS = 400


def update_symbols(
    symbols: Union[str, Iterable[str]],
    db_path: str = "stocks.db",
    interval: str = "1d",
    start: str = "2015-01-01",
    end: Optional[str] = None,
    indicators: Optional[List[IndicatorSpec]] = None,
) -> pd.DataFrame:
    """Descarga datos nuevos, recalcula indicadores y guarda en SQLite.

    Si el símbolo ya existe en la BD solo se descargan las barras posteriores a
    la última guardada (salvo que `start` sea anterior al primer dato guardado:
    entonces se vuelve a descargar todo desde `start`); los indicadores se recalculan sobre una ventana con
    histórico previo para que sean correctos. Devuelve el DataFrame completo
    (precios + indicadores) de los símbolos pedidos.
    """
    if isinstance(symbols, str):
        symbols = [symbols]
    symbols = [s.upper() for s in symbols]

    with StockDB(db_path) as db:
        for sym in symbols:
            last = db.last_date(sym, interval)
            first = db.first_date(sym, interval)
            if last is None or pd.Timestamp(start) < first:
                sym_start = start  # símbolo nuevo o `start` anterior al histórico guardado
            else:
                sym_start = (last + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            new = download_prices(sym, start=sym_start, end=end, interval=interval)
            if new.empty:
                continue
            db.save_prices(new, interval)
            hist = db.load(sym, interval, with_indicators=False).tail(WARMUP_BARS + len(new))
            full = add_indicators(hist, indicators)
            ind_cols = [c for c in full.columns if c not in hist.columns]
            db.save_indicators(full[["symbol", "date"] + ind_cols], interval)
        return db.load(symbols, interval)
