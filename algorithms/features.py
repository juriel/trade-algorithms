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


# ----------------------------- filtros de mercado (columnas `mkt_*`) -----------------------------
# Requieren la BD con datos de mercado (`update_market`) y `StockDB.load(..., with_market=True)`.
# Si falta el dato de un día (NaN) la condición es falsa: ese día no se compra.

def stress_score(df: pd.DataFrame, vix_pctrank_min: float = 90.0, spx_rsi_max: float = 31.0,
                 breadth_max: float = 25.0, spx_ret20_max: float = -8.0) -> pd.Series:
    """Cuántas de 4 señales de capitulación del mercado están activas (0-4): VIX en su percentil
    alto del año, RSI(14) del S&P 500 bajo, amplitud baja (% de acciones sobre su SMA200) y caída del
    S&P 500 en 20 días."""
    return ((df["mkt_vix_pctrank"] >= vix_pctrank_min).astype(int)
            + (df["mkt_spx_rsi14"] <= spx_rsi_max).astype(int)
            + (df["mkt_breadth200"] <= breadth_max).astype(int)
            + (df["mkt_spx_ret20"] <= spx_ret20_max).astype(int))


def stress_expansion(df: pd.DataFrame, vix_ratio50_min: float = 1.3, credit_ret20_max: float = -4.0,
                     spx_ret20_max: float = -8.0) -> pd.Series:
    """Estrés en expansión: VIX sobre su media de 50 días, crédito riesgoso (HYG/LQD) cayendo
    o S&P 500 en caída fuerte a 20 días."""
    return ((df["mkt_vix_ratio50"] >= vix_ratio50_min) | (df["mkt_credit_ret20"] <= credit_ret20_max)
            | (df["mkt_spx_ret20"] <= spx_ret20_max))


def healthy_bull(df: pd.DataFrame, min_breadth: float = 45.0, min_curve: float = 0.7) -> pd.Series:
    """Régimen alcista sano: S&P 500 sobre su SMA200, amplitud suficiente y curva de tasas no invertida."""
    return ((df["mkt_spx_above_sma200"] == 1) & (df["mkt_breadth200"] >= min_breadth)
            & (df["mkt_curve"] >= min_curve))


# ----------------------------- volumen, calendario y fuerza relativa -----------------------------
def volume_ratio(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Volumen del día / promedio de los `n` días ANTERIORES (>2,5 = volumen climático)."""
    avg = df["volume"].rolling(n).mean().shift(1)
    return df["volume"] / avg.replace(0, np.nan)


def business_days_left(df: pd.DataFrame) -> pd.Series:
    """Días hábiles (lun-vie, sin festivos) que quedan del mes DESPUÉS de cada día. 0 = último día hábil.
    Es calendario: se conoce de antemano, no mira datos futuros."""
    d = pd.DatetimeIndex(df["date"])
    end = (d + pd.offsets.MonthEnd(0) + pd.Timedelta(days=1)).values.astype("datetime64[D]")
    return pd.Series(np.busday_count(d.values.astype("datetime64[D]"), end) - 1, index=df.index)


def rel_strength(df: pd.DataFrame, n: int = 120) -> pd.Series:
    """Retorno % de la acción en `n` días menos el del S&P 500 (`mkt_spx_ret{n}`, n = 60 o 120)."""
    return df["close"].pct_change(n) * 100 - df[f"mkt_spx_ret{n}"]
