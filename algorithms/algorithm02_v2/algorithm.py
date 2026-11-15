"""Algoritmo 02_v2 - Tendencia con filtro de volatilidad (ancho de Bollinger)

Mejora de 02. Análisis: el cuartil de bandas más anchas (>18%) dio 2.0% por operación contra 0.9% en el resto, y
las pérdidas llegan a -38%. Cambios: exige ancho de banda mínimo y mantiene la salida por SMA50; el stop por
ATR queda disponible (stop_atr_mult) pero desactivado porque no mejoró en el análisis.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P02V2(Params):
    target_pct: Optional[float] = 0.25
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    adx_min: float = 20.0
    min_bb_width: float = 12.0
    stop_atr_mult: Optional[float] = None
    target_atr_mult: Optional[float] = None


class Algorithm02V2(Algorithm):
    name = "algorithm02_v2"
    description = "Tendencia con filtro de volatilidad (ancho de Bollinger)"
    params_cls = P02V2
    requires = ["sma_20", "sma_50", "sma_200", "adx_14", "macd_hist", "bb_upper", "bb_lower", "bb_middle", "atr_14"]

    def buy_signal(self, df):
        return ((df["sma_20"] > df["sma_50"]) & (df["close"] > df["sma_200"]) & (df["adx_14"] > self.p.adx_min)
                & (df["macd_hist"] > 0) & ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100 >= self.p.min_bb_width))

    def sell_signal(self, df):
        return df["close"] < df["sma_50"]
