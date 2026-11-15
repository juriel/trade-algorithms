"""Algoritmo 03a_v1_r2 - Bollinger+RSI con IBS, régimen de volatilidad y límite de 5 días

Base 03a_v1. Añade IBS bajo, filtro de régimen de volatilidad y reduce el tiempo máximo a 5 días. Mismas salidas por ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03aV1R2(Params):
    target_pct: Optional[float] = 0.04
    max_hold_days: Optional[int] = 5
    stop_pct: Optional[float] = None
    rsi_max: float = 30.0
    min_atr_pct: float = 2.0
    max_atr_regime: float = 1.8
    ibs_max: float = 0.25
    target_atr_mult: Optional[float] = 1.5
    stop_atr_mult: Optional[float] = 2.5


class Algorithm03aV1R2(Algorithm):
    name = "algorithm03a_v1_r2"
    description = "Bollinger+RSI con IBS, régimen de volatilidad y límite de 5 días"
    params_cls = P03aV1R2
    requires = ["bb_lower", "bb_middle", "rsi_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["rsi_14"] < self.p.rsi_max)
                & (F.atr_pct(df) >= self.p.min_atr_pct) & (F.atr_regime(df) <= self.p.max_atr_regime)
                & (F.ibs(df) <= self.p.ibs_max))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
