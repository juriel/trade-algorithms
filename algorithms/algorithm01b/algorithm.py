"""Algoritmo 01b - RSI + Estocástico, sin filtro de tendencia.

Doble confirmación de sobreventa (RSI y Estocástico).
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class Params01b(Params):
    target_pct: float = 0.04
    max_hold_days: int = 8
    rsi_buy: float = 35.0
    stoch_max: float = 20.0
    rsi_sell: float = 60.0


class Algorithm01b(Algorithm):
    name = "algorithm01b"
    description = "RSI + Estocástico, sin filtro de tendencia"
    params_cls = Params01b
    requires = ["rsi_14", "stoch_k"]

    def buy_signal(self, df):
        return (df["rsi_14"] < self.p.rsi_buy) & (df["stoch_k"] < self.p.stoch_max)

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
