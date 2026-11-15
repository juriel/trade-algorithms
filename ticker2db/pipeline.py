"""Pipeline completo: descarga -> indicadores -> SQLite (incremental)."""
from __future__ import annotations

from typing import Iterable, List, Optional, Union

import pandas as pd

from .downloader import download_prices
from .indicators import DEFAULT_INDICATORS, IndicatorSpec, add_indicators
from .market import market_symbols
from .storage import StockDB

# Barras previas necesarias para que los indicadores largos (SMA 200...) converjan.
WARMUP_BARS = 400
VOLUME_INDICATORS = {"OBV", "MFI", "AD", "ADOSC"}  # no tienen sentido en series sin volumen (p.ej. ^VIX)


def update_symbols(
    symbols: Union[str, Iterable[str]],
    db_path: str = "stocks.db",
    interval: str = "1d",
    start: str = "2015-01-01",
    end: Optional[str] = None,
    indicators: Optional[List[IndicatorSpec]] = None,
    return_data: bool = True,
) -> Optional[pd.DataFrame]:
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
            inds = DEFAULT_INDICATORS if indicators is None else indicators
            if hist["volume"].fillna(0).sum() == 0:
                inds = [i for i in inds if i[0].upper() not in VOLUME_INDICATORS]
            full = add_indicators(hist, inds)
            ind_cols = [c for c in full.columns if c not in hist.columns]
            db.save_indicators(full[["symbol", "date"] + ind_cols], interval)
        return db.load(symbols, interval) if return_data else None


def update_market(
    db_path: str = "stocks.db",
    categories: Optional[Iterable[str]] = None,
    interval: str = "1d",
    start: str = "1900-01-01",
    end: Optional[str] = None,
) -> dict:
    """Descarga índices, VIX, DXY, tasas y ETFs (ver `ticker2db.market.MARKET_SYMBOLS`) a la base.

    Los símbolos se registran como "de mercado": no aparecen en `StockDB.symbols()`. Es incremental,
    como `update_symbols`. Devuelve {"ok": [...], "fallidos": {símbolo: error}}.
    """
    items = market_symbols(categories)
    with StockDB(db_path) as db:
        db.register_symbols(items)
    ok, failed = [], {}
    for sym, _, _ in items:
        try:
            update_symbols([sym], db_path, interval, start, end, return_data=False)
            ok.append(sym)
        except Exception as e:  # un símbolo con datos raros no debe detener al resto
            failed[sym] = f"{type(e).__name__}: {e}"
    with StockDB(db_path) as db:
        have = set(db.market_symbols())
    failed.update({s: "sin datos" for s in ok if s not in have})
    return {"ok": [s for s in ok if s in have], "fallidos": failed}
