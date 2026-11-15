"""Algoritmo 03a_v2_r2 - Bollinger+RSI con IBS y stops cortos por ATR

Base 03a_v2. Añade IBS <= ibs_max, límite de tiempo de 5 días (la mayoría de las reversiones se resuelve en 3-5\ndías; pasado ese plazo la hipótesis suele ser errónea) y stop/meta en múltiplos de ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03aV2R2(Params):
    target_pct: Optional[float] = 0.05
    max_hold_days: Optional[int] = 5
    stop_pct: Optional[float] = None
    rsi_max: float = 30.0
    min_bb_width: float = 12.0
    max_dist_sma50: float = -9.0
    ibs_max: float = 0.25
    target_atr_mult: Optional[float] = 1.5
    stop_atr_mult: Optional[float] = 2.0


class Algorithm03aV2R2(Algorithm):
    name = "algorithm03a_v2_r2"
    description = "Bollinger+RSI con IBS y stops cortos por ATR"
    params_cls = P03aV2R2
    requires = ["bb_lower", "bb_middle", "bb_upper", "rsi_14", "sma_50", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["rsi_14"] < self.p.rsi_max)
                & (F.bb_width(df) >= self.p.min_bb_width) & (F.ibs(df) <= self.p.ibs_max)
                & ((df["close"] / df["sma_50"] - 1) * 100 <= self.p.max_dist_sma50))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
