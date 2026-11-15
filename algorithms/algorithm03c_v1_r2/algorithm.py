"""Algoritmo 03c_v1_r2 - Bollinger+MFI con MFI más profundo que el RSI

Base 03c_v1. Exige que el MFI esté más bajo que el RSI(14) (salida de dinero mayor que la de precio): sobreventa\nrespaldada por volumen. Mismas salidas por ATR, con tiempo máximo reducido a 6 días.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03cV1R2(Params):
    target_pct: Optional[float] = 0.04
    max_hold_days: Optional[int] = 6
    stop_pct: Optional[float] = None
    mfi_max: float = 20.0
    mfi_rsi_gap: float = 5.0
    min_atr_pct: float = 2.0
    target_atr_mult: Optional[float] = 1.5
    stop_atr_mult: Optional[float] = 2.5


class Algorithm03cV1R2(Algorithm):
    name = "algorithm03c_v1_r2"
    description = "Bollinger+MFI con MFI más profundo que el RSI"
    params_cls = P03cV1R2
    requires = ["bb_lower", "bb_middle", "mfi_14", "rsi_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["mfi_14"] < self.p.mfi_max)
                & (df["mfi_14"] <= df["rsi_14"] - self.p.mfi_rsi_gap) & (F.atr_pct(df) >= self.p.min_atr_pct))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
