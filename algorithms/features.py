"""Indicadores auxiliares para los algoritmos (se calculan sobre OHLC + columnas de la BD).

Todas las funciones reciben el DataFrame del símbolo y devuelven una Serie alineada con él,
calculada con datos hasta el cierre de cada día (sin mirar al futuro).
"""
import numpy as np
import pandas as pd
import talib


def ibs(df: pd.DataFrame) -> pd.Series:
    """Internal Bar Strength: (cierre - mínimo) / (máximo - mínimo). Cerca de 0 = cierre en el piso del día."""
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return (df["close"] - df["low"]) / rng


def rsi(df: pd.DataFrame, period: int = 2) -> pd.Series:
    """RSI de periodo arbitrario (el RSI(2) de Connors no está precalculado en la BD)."""
    return pd.Series(talib.RSI(df["close"].to_numpy(float), period), index=df.index)


def sma(df: pd.DataFrame, period: int) -> pd.Series:
    return df["close"].rolling(period).mean()


def atr_pct(df: pd.DataFrame) -> pd.Series:
    return df["atr_14"] / df["close"] * 100


def atr_regime(df: pd.DataFrame, window: int = 100) -> pd.Series:
    """ATR% actual / su media de `window` días. >1.5-2 = volatilidad inestable (sustituto de un filtro VIX)."""
    a = atr_pct(df)
    return a / a.rolling(window).mean()


def bb_width(df: pd.DataFrame) -> pd.Series:
    return (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100


def bullish_reversal(df: pd.DataFrame) -> pd.Series:
    """Vela alcista que cierra por encima del cierre anterior."""
    return (df["close"] > df["open"]) & (df["close"] > df["close"].shift(1))


def back_inside_lower(df: pd.DataFrame) -> pd.Series:
    """Ayer cerró bajo la banda inferior de Bollinger y hoy vuelve a cerrar dentro de ella."""
    return (df["close"] > df["bb_lower"]) & (df["close"].shift(1) < df["bb_lower"].shift(1))
