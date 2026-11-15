"""Algoritmo 03b - Bollinger inferior + CCI.

Cierre bajo Bollinger inferior con CCI profundo; sale cuando el CCI se recupera.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params03b(Params):
    target_pct: float = 0.04
    max_hold_days: int = 15
    cci_buy: float = -100.0
    cci_sell: float = 0.0


class Algorithm03b(Algorithm):
    name = "algorithm03b"
    description = "Bollinger inferior + CCI"
    params_cls = Params03b
    requires = ["bb_lower", "cci_14"]

    def buy_signal(self, df):
        return (df["close"] < df["bb_lower"]) & (df["cci_14"] < self.p.cci_buy)

    def sell_signal(self, df):
        return df["cci_14"] > self.p.cci_sell
