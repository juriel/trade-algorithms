"""Cálculo de indicadores técnicos con TA-Lib.

Cada entrada de la configuración es (función_talib, kwargs). Los nombres de
las columnas de salida se generan a partir de la función y sus parámetros,
p.ej. SMA(timeperiod=20) -> "sma_20", MACD -> "macd", "macd_signal", "macd_hist".
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import talib
from talib import abstract

IndicatorSpec = Tuple[str, Dict]

DEFAULT_INDICATORS: List[IndicatorSpec] = [
    ("SMA", {"timeperiod": 20}),
    ("SMA", {"timeperiod": 50}),
    ("SMA", {"timeperiod": 200}),
    ("EMA", {"timeperiod": 12}),
    ("EMA", {"timeperiod": 26}),
    ("RSI", {"timeperiod": 14}),
    ("MACD", {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}),
    ("BBANDS", {"timeperiod": 20, "nbdevup": 2, "nbdevdn": 2}),
    ("ATR", {"timeperiod": 14}),
    ("ADX", {"timeperiod": 14}),
    ("STOCH", {}),
    ("CCI", {"timeperiod": 14}),
    ("OBV", {}),
    ("MFI", {"timeperiod": 14}),
]

_SUFFIXES = {
    "MACD": ["macd", "macd_signal", "macd_hist"],
    "BBANDS": ["bb_upper", "bb_middle", "bb_lower"],
    "STOCH": ["stoch_k", "stoch_d"],
}


def _column_names(name: str, kwargs: Dict, n_outputs: int, outputs: List[str]) -> List[str]:
    key = name.upper()
    if key in _SUFFIXES and len(_SUFFIXES[key]) == n_outputs:
        return list(_SUFFIXES[key])
    tag = "_".join(str(v) for k, v in kwargs.items() if k == "timeperiod")
    base = f"{name.lower()}_{tag}" if tag else name.lower()
    if n_outputs == 1:
        return [base]
    return [f"{base}_{o}" for o in outputs]


def _compute_one(df: pd.DataFrame, name: str, kwargs: Dict) -> pd.DataFrame:
    func = abstract.Function(name.upper())
    inputs = {k: df[k].to_numpy(dtype="float64") for k in ("open", "high", "low", "close", "volume")}
    out = func(inputs, **kwargs)
    outputs = list(func.output_names)
    arrays = [out] if isinstance(out, np.ndarray) else list(out)
    cols = _column_names(name, kwargs, len(arrays), outputs)
    return pd.DataFrame(dict(zip(cols, arrays)), index=df.index)


def add_indicators(
    df: pd.DataFrame,
    indicators: Optional[List[IndicatorSpec]] = None,
) -> pd.DataFrame:
    """Añade indicadores a un DataFrame OHLCV (formato largo con `symbol`).

    Los indicadores se calculan por símbolo, ordenados por fecha. Devuelve un
    DataFrame con las columnas originales más las de los indicadores.
    """
    indicators = DEFAULT_INDICATORS if indicators is None else indicators
    if df.empty:
        return df.copy()

    def per_symbol(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("date").reset_index(drop=True)
        parts = [g] + [_compute_one(g, n, kw) for n, kw in indicators]
        return pd.concat(parts, axis=1)

    if "symbol" in df.columns:
        return pd.concat([per_symbol(g) for _, g in df.groupby("symbol", sort=False)],
                         ignore_index=True)
    return per_symbol(df)


def available_functions() -> List[str]:
    return talib.get_functions()
