"""Algoritmo 02c - Retroceso dentro de una tendencia alcista.

Tendencia alcista (SMA50 > SMA200) y retroceso bajo la SMA20.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params02c(Params):
    target_pct: float = 0.06
    max_hold_days: int = 15
    rsi_max: float = 50.0
    rsi_sell: float = 70.0


class Algorithm02c(Algorithm):
    name = "algorithm02c"
    description = "Retroceso dentro de una tendencia alcista"
    params_cls = Params02c
    requires = ["sma_20", "sma_50", "sma_200", "rsi_14"]

    def buy_signal(self, df):
        return ((df["sma_50"] > df["sma_200"]) & (df["close"] > df["sma_200"])
                & (df["close"] < df["sma_20"]) & (df["rsi_14"] < self.p.rsi_max))

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
