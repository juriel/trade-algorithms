"""Algoritmo 01a - Rebote RSI con giro al alza.

Sobreventa RSI con SMA200 y, opcionalmente, RSI ya girando al alza.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params01a(Params):
    target_pct: float = 0.05
    max_hold_days: int = 10
    rsi_buy: float = 30.0
    rsi_sell: float = 65.0
    require_rising: bool = True


class Algorithm01a(Algorithm):
    name = "algorithm01a"
    description = "Rebote RSI con giro al alza"
    params_cls = Params01a
    requires = ["rsi_14", "sma_200"]

    def buy_signal(self, df):
        sig = (df["rsi_14"] < self.p.rsi_buy) & (df["close"] > df["sma_200"])
        if self.p.require_rising:
            sig &= df["rsi_14"] > df["rsi_14"].shift(1)
        return sig

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
