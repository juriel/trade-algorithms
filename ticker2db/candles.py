"""Patrones de velas japonesas con TA-Lib (familia `CDL*`, 61 patrones).

Cada patrón devuelve, por día: +100 (señal alcista), -100 (señal bajista) o 0 (sin patrón); algunos
patrones usan también +-200 (confirmación). El patrón de un día solo usa velas hasta ese día
(se puede usar al cierre sin mirar al futuro). Las columnas se llaman `cdl_<nombre>`,
p.ej. `CDLENGULFING` -> `cdl_engulfing`, `CDL3WHITESOLDIERS` -> `cdl_3whitesoldiers`.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import talib
from talib import abstract

PREFIX = "cdl_"

# Patrones más usados (subconjunto cómodo para empezar)
COMMON_PATTERNS = [
    "CDLDOJI", "CDLDRAGONFLYDOJI", "CDLGRAVESTONEDOJI", "CDLHAMMER", "CDLINVERTEDHAMMER", "CDLHANGINGMAN",
    "CDLSHOOTINGSTAR", "CDLENGULFING", "CDLHARAMI", "CDLHARAMICROSS", "CDLPIERCING", "CDLDARKCLOUDCOVER",
    "CDLMORNINGSTAR", "CDLEVENINGSTAR", "CDLMORNINGDOJISTAR", "CDLEVENINGDOJISTAR", "CDL3WHITESOLDIERS",
    "CDL3BLACKCROWS", "CDL3INSIDE", "CDL3OUTSIDE", "CDLMARUBOZU", "CDLSPINNINGTOP", "CDLBELTHOLD",
    "CDLABANDONEDBABY", "CDLKICKING", "CDLTRISTAR",
]


# Patrones de indecisión: TA-Lib devuelve siempre +100 cuando aparecen (no son alcistas, solo indican que
# el patrón está presente). `candle_summary` los excluye del conteo alcista/bajista por defecto.
NEUTRAL_PATTERNS = [
    "CDLDOJI", "CDLLONGLEGGEDDOJI", "CDLRICKSHAWMAN", "CDLDRAGONFLYDOJI", "CDLGRAVESTONEDOJI", "CDLTAKURI",
]


def pattern_functions() -> List[str]:
    """Nombres de todas las funciones de patrones de velas de TA-Lib (CDL...)."""
    return list(talib.get_function_groups()["Pattern Recognition"])


def pattern_info() -> Dict[str, str]:
    """{función: nombre descriptivo en inglés} p.ej. {'CDLHAMMER': 'Hammer'}."""
    return {f: abstract.Function(f).info["display_name"] for f in pattern_functions()}


def column_name(function: str) -> str:
    return PREFIX + function.upper()[3:].lower()


def _resolve(patterns: Optional[Iterable[str]]) -> List[str]:
    allp = set(pattern_functions())
    if patterns is None:
        return pattern_functions()
    out = []
    for p in patterns:
        p = p.upper()
        p = p if p.startswith("CDL") else "CDL" + p
        if p not in allp:
            raise ValueError(f"Patrón desconocido: {p}. Ver ticker2db.candles.pattern_functions()")
        out.append(p)
    return out


def _compute(df: pd.DataFrame, funcs: List[str]) -> pd.DataFrame:
    o, h, l, c = (df[k].to_numpy(dtype="float64") for k in ("open", "high", "low", "close"))
    cols = {column_name(f): getattr(talib, f)(o, h, l, c).astype("int32") for f in funcs}
    return pd.DataFrame(cols, index=df.index)


def add_candle_patterns(df: pd.DataFrame, patterns: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Añade columnas `cdl_*` a un DataFrame OHLC (formato largo con `symbol` y `date`, como en
    `add_indicators`). `patterns`: nombres como "CDLENGULFING" o "ENGULFING"; por defecto los 61."""
    funcs = _resolve(patterns)
    if df.empty:
        return df.copy()

    def per_symbol(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("date").reset_index(drop=True)
        return pd.concat([g, _compute(g, funcs)], axis=1)

    if "symbol" in df.columns:
        return pd.concat([per_symbol(g) for _, g in df.groupby("symbol", sort=False)], ignore_index=True)
    return per_symbol(df)


def candle_summary(df: pd.DataFrame, include_neutral: bool = False) -> pd.DataFrame:
    """Resumen de las columnas `cdl_*` presentes: nº de patrones alcistas, bajistas y balance neto.

    Devuelve `cdl_bull_count`, `cdl_bear_count` y `cdl_net` (alcistas - bajistas), alineado con `df`.
    Los patrones de indecisión (`NEUTRAL_PATTERNS`: doji y similares, que TA-Lib marca siempre +100) no
    cuentan como alcistas salvo que `include_neutral=True`.
    """
    skip = {"cdl_bull_count", "cdl_bear_count", "cdl_net"}
    if not include_neutral:
        skip |= {column_name(f) for f in NEUTRAL_PATTERNS}
    cols = [c for c in df.columns if c.startswith(PREFIX) and c not in skip]
    if not cols:
        raise ValueError("El DataFrame no tiene columnas cdl_* direccionales; usa add_candle_patterns o load(with_candles=True)")
    m = df[cols].to_numpy()
    bull, bear = (m > 0).sum(axis=1), (m < 0).sum(axis=1)
    return pd.DataFrame({"cdl_bull_count": bull, "cdl_bear_count": bear, "cdl_net": bull - bear}, index=df.index)
