"""Algoritmo 03a_v2_r1 - Bollinger+RSI(2) de Connors con salida rápida

Base 03a_v2. Sustituye el RSI(14) por el RSI(2) (Connors: RSI2 < 10) y sale cuando el cierre supera la media de 5\ndías, como en la regla original de Connors. Mantiene caída profunda bajo la SMA50 y bandas anchas.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03aV2R1(Params):
    target_pct: Optional[float] = 0.05
    max_hold_days: Optional[int] = 6
    stop_pct: Optional[float] = 0.07
    rsi2_max: float = 10.0
    min_bb_width: float = 12.0
    max_dist_sma50: float = -9.0
    use_trend_filter: bool = False
    exit_sma: int = 5


class Algorithm03aV2R1(Algorithm):
    name = "algorithm03a_v2_r1"
    description = "Bollinger+RSI(2) de Connors con salida rápida"
    params_cls = P03aV2R1
    requires = ["bb_lower", "bb_upper", "bb_middle", "sma_50", "sma_200"]

    def buy_signal(self, df):
        sig = ((df["close"] < df["bb_lower"]) & (F.rsi(df, 2) < self.p.rsi2_max)
               & (F.bb_width(df) >= self.p.min_bb_width)
               & ((df["close"] / df["sma_50"] - 1) * 100 <= self.p.max_dist_sma50))
        if self.p.use_trend_filter:
            sig &= df["close"] > df["sma_200"]
        return sig

    def sell_signal(self, df):
        return df["close"] > F.sma(df, self.p.exit_sma)
