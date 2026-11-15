"""Algoritmo 02 - Seguimiento de tendencia (cruce de medias + MACD + ADX).

COMPRA (apertura): ayer SMA20 > SMA50, cierre > SMA200, MACD hist > 0 y ADX > `adx_min`.
VENTA: meta +`target_pct`, o a la apertura si ayer el cierre quedó bajo la SMA50.
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params02(Params):
    # Valores por defecto de respaldo; los valores reales se editan en variables.cfg
    adx_min: float = 20.0
    use_macd_filter: bool = True
    target_pct: float = 0.15
    max_hold_days: Optional[int] = None


class Algorithm02(Algorithm):
    name = "algorithm02"
    description = "Tendencia: SMA20>SMA50, sobre SMA200, MACD y ADX"
    params_cls = Params02
    requires = ["sma_20", "sma_50", "sma_200", "macd_hist", "adx_14"]

    def buy_signal(self, df):
        sig = (df["sma_20"] > df["sma_50"]) & (df["close"] > df["sma_200"]) & (df["adx_14"] > self.p.adx_min)
        if self.p.use_macd_filter:
            sig &= df["macd_hist"] > 0
        return sig

    def sell_signal(self, df):
        return df["close"] < df["sma_50"]
