"""Algoritmo 02a - Tendencia por cruce de EMAs.

EMA12 > EMA26, sobre SMA50 y ADX; sale cuando las EMAs se cruzan a la baja.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params02a(Params):
    target_pct: float = 0.12
    max_hold_days: Optional[int] = None
    adx_min: float = 20.0


class Algorithm02a(Algorithm):
    name = "algorithm02a"
    description = "Tendencia por cruce de EMAs"
    params_cls = Params02a
    requires = ["ema_12", "ema_26", "sma_50", "adx_14"]

    def buy_signal(self, df):
        return (df["ema_12"] > df["ema_26"]) & (df["close"] > df["sma_50"]) & (df["adx_14"] > self.p.adx_min)

    def sell_signal(self, df):
        return df["ema_12"] < df["ema_26"]
