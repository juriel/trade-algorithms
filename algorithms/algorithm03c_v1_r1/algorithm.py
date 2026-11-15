"""Algoritmo 03c_v1_r1 - Bollinger+MFI con filtro de régimen de volatilidad

Base 03c_v1. Evita comprar cuando la volatilidad está inestable (ATR% actual > max_atr_regime veces su media de\n100 días): sustituto del filtro VIX, porque ahí 'lo sobrevendido puede seguir sobrevendido'. Mismas salidas por ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03cV1R1(Params):
    target_pct: Optional[float] = 0.04
    max_hold_days: Optional[int] = 10
    stop_pct: Optional[float] = None
    mfi_max: float = 20.0
    min_atr_pct: float = 2.0
    max_atr_regime: float = 1.8
    target_atr_mult: Optional[float] = 1.5
    stop_atr_mult: Optional[float] = 2.5


class Algorithm03cV1R1(Algorithm):
    name = "algorithm03c_v1_r1"
    description = "Bollinger+MFI con filtro de régimen de volatilidad"
    params_cls = P03cV1R1
    requires = ["bb_lower", "bb_middle", "mfi_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["mfi_14"] < self.p.mfi_max)
                & (F.atr_pct(df) >= self.p.min_atr_pct) & (F.atr_regime(df) <= self.p.max_atr_regime))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
