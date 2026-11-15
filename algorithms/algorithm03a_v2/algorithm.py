"""Algoritmo 03a_v2 - Bollinger+RSI solo en caídas profundas con bandas anchas

Mejora de 03a. Análisis: las entradas con el cierre muy por debajo de la SMA50 (< -9%) y bandas anchas
rindieron más (1.2% vs 0.5%). Cambios: exige ambas condiciones y añade stop fijo.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P03aV2(Params):
    target_pct: Optional[float] = 0.05
    max_hold_days: Optional[int] = 10
    stop_pct: Optional[float] = 0.07
    rsi_max: float = 30.0
    min_bb_width: float = 12.0
    max_dist_sma50: float = -9.0


class Algorithm03aV2(Algorithm):
    name = "algorithm03a_v2"
    description = "Bollinger+RSI solo en caídas profundas con bandas anchas"
    params_cls = P03aV2
    requires = ["bb_lower", "bb_middle", "rsi_14", "sma_50"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["rsi_14"] < self.p.rsi_max)
                & ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100 >= self.p.min_bb_width)
                & ((df["close"] / df["sma_50"] - 1) * 100 <= self.p.max_dist_sma50))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
