"""Algoritmo 03a - Bollinger inferior + RSI.

Cierre bajo Bollinger inferior con RSI bajo; sale en la banda media.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params03a(Params):
    target_pct: float = 0.04
    max_hold_days: int = 15
    rsi_max: float = 30.0


class Algorithm03a(Algorithm):
    name = "algorithm03a"
    description = "Bollinger inferior + RSI"
    params_cls = Params03a
    requires = ["bb_lower", "bb_middle", "rsi_14"]

    def buy_signal(self, df):
        return (df["close"] < df["bb_lower"]) & (df["rsi_14"] < self.p.rsi_max)

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
