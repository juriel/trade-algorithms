"""Algoritmo 03c - Bollinger inferior + MFI (volumen).

Cierre bajo Bollinger inferior con flujo de dinero (MFI) bajo.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params03c(Params):
    target_pct: float = 0.05
    max_hold_days: int = 15
    mfi_max: float = 20.0
    use_trend_filter: bool = False


class Algorithm03c(Algorithm):
    name = "algorithm03c"
    description = "Bollinger inferior + MFI (volumen)"
    params_cls = Params03c
    requires = ["bb_lower", "bb_middle", "mfi_14", "sma_200"]

    def buy_signal(self, df):
        sig = (df["close"] < df["bb_lower"]) & (df["mfi_14"] < self.p.mfi_max)
        if self.p.use_trend_filter:
            sig &= df["close"] > df["sma_200"]
        return sig

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
