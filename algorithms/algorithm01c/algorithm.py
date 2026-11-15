"""Algoritmo 01c - RSI bajo con giro del MACD sobre SMA50.

RSI bajo, histograma MACD mejorando y precio sobre SMA50.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params01c(Params):
    target_pct: float = 0.06
    max_hold_days: int = 12
    rsi_buy: float = 40.0
    rsi_sell: float = 65.0


class Algorithm01c(Algorithm):
    name = "algorithm01c"
    description = "RSI bajo con giro del MACD sobre SMA50"
    params_cls = Params01c
    requires = ["rsi_14", "macd_hist", "sma_50"]

    def buy_signal(self, df):
        return ((df["rsi_14"] < self.p.rsi_buy) & (df["macd_hist"] > df["macd_hist"].shift(1))
                & (df["close"] > df["sma_50"]))

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
