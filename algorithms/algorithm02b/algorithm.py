"""Algoritmo 02b - Ruptura de Bollinger con ADX.

Compra rupturas sobre la banda superior; sale al perder la banda media.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params02b(Params):
    target_pct: float = 0.1
    max_hold_days: int = 20
    adx_min: float = 25.0


class Algorithm02b(Algorithm):
    name = "algorithm02b"
    description = "Ruptura de Bollinger con ADX"
    params_cls = Params02b
    requires = ["bb_upper", "bb_middle", "adx_14", "sma_200"]

    def buy_signal(self, df):
        return (df["close"] > df["bb_upper"]) & (df["adx_14"] > self.p.adx_min) & (df["close"] > df["sma_200"])

    def sell_signal(self, df):
        return df["close"] < df["bb_middle"]
