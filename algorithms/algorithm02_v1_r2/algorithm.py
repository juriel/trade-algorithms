"""Algoritmo 02_v1_r2 - Tendencia con bandas anchas, Chandelier adaptativo al régimen de volatilidad

Base 02_v1. Observación propia: las bandas de Bollinger anchas rinden el doble. Además el trailing se ensancha cuando la\nvolatilidad está expandida (k * ATR-régimen, acotado) para no ser expulsado por ruido en tramos violentos.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P02V1R2(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    adx_min: float = 20.0
    min_macd_pct: float = 0.5
    min_bb_width: float = 12.0
    chandelier_window: int = 22
    chandelier_k: float = 4.0
    max_k_scale: float = 1.5


class Algorithm02V1R2(Algorithm):
    name = "algorithm02_v1_r2"
    description = "Tendencia con bandas anchas, Chandelier adaptativo al régimen de volatilidad"
    params_cls = P02V1R2
    requires = ["sma_20", "sma_50", "sma_200", "adx_14", "macd_hist", "atr_14", "bb_upper", "bb_lower", "bb_middle"]

    def buy_signal(self, df):
        return ((df["sma_20"] > df["sma_50"]) & (df["close"] > df["sma_200"]) & (df["adx_14"] > self.p.adx_min)
                & (df["macd_hist"] / df["close"] * 100 >= self.p.min_macd_pct)
                & (F.bb_width(df) >= self.p.min_bb_width))

    def sell_signal(self, df):
        scale = F.atr_regime(df).clip(lower=1.0, upper=self.p.max_k_scale).fillna(1.0)
        return (df["close"] < df["close"].rolling(self.p.chandelier_window).max()
                - self.p.chandelier_k * scale * df["atr_14"])
