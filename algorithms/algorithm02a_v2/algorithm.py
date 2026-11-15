"""Algoritmo 02a_v2 - Cruce de EMAs con filtro de volatilidad y salida Chandelier amplia

Mejora de 02a. Análisis: bandas anchas (>18%) rindieron 1.8% frente a ~1% del resto y la salida por cruce
de EMAs era tardía. Cambios: exige ADX y ancho de banda mínimos y sale con trailing Chandelier amplio, sin meta.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P02aV2(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    adx_min: float = 25.0
    min_bb_width: float = 12.0
    chandelier_window: int = 22
    chandelier_k: float = 5.0


class Algorithm02aV2(Algorithm):
    name = "algorithm02a_v2"
    description = "Cruce de EMAs con filtro de volatilidad y salida Chandelier amplia"
    params_cls = P02aV2
    requires = ["ema_12", "ema_26", "sma_50", "adx_14", "bb_upper", "bb_lower", "bb_middle", "atr_14"]

    def buy_signal(self, df):
        return ((df["ema_12"] > df["ema_26"]) & (df["close"] > df["sma_50"]) & (df["adx_14"] > self.p.adx_min)
                & ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100 >= self.p.min_bb_width))

    def sell_signal(self, df):
        return df["close"] < df["close"].rolling(self.p.chandelier_window).max() - self.p.chandelier_k * df["atr_14"]
