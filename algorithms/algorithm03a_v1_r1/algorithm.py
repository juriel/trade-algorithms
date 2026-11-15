"""Algoritmo 03a_v1_r1 - Bollinger+RSI con vela de confirmación

Base 03a_v1. Exige que el día de la señal sea una vela alcista que cierre sobre el cierre anterior tras un cierre bajo\nla banda con RSI bajo (confirmación de giro, evita comprar mientras la caída continúa). Mismas salidas por ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03aV1R1(Params):
    target_pct: Optional[float] = 0.04
    max_hold_days: Optional[int] = 10
    stop_pct: Optional[float] = None
    rsi_max: float = 30.0
    min_atr_pct: float = 2.0
    target_atr_mult: Optional[float] = 1.5
    stop_atr_mult: Optional[float] = 2.5


class Algorithm03aV1R1(Algorithm):
    name = "algorithm03a_v1_r1"
    description = "Bollinger+RSI con vela de confirmación"
    params_cls = P03aV1R1
    requires = ["bb_lower", "bb_middle", "rsi_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"].shift(1) < df["bb_lower"].shift(1)) & (df["rsi_14"].shift(1) < self.p.rsi_max)
                & F.bullish_reversal(df) & (F.atr_pct(df) >= self.p.min_atr_pct))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
