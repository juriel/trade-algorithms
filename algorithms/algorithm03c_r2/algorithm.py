"""Algoritmo 03c_r2 - Bollinger+MFI+RSI con régimen de volatilidad y stop ATR

Base 03c. Doble confirmación de sobreventa (MFI y RSI(14)), filtro de régimen de volatilidad (evita volatilidad\ninestable) y stop de 2 ATR; sale en la banda media; máximo 8 días.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03cR2(Params):
    target_pct: Optional[float] = 0.04
    max_hold_days: Optional[int] = 8
    stop_pct: Optional[float] = None
    mfi_max: float = 20.0
    rsi_max: float = 35.0
    max_atr_regime: float = 1.8
    stop_atr_mult: Optional[float] = 2.0


class Algorithm03cR2(Algorithm):
    name = "algorithm03c_r2"
    description = "Bollinger+MFI+RSI con régimen de volatilidad y stop ATR"
    params_cls = P03cR2
    requires = ["bb_lower", "bb_middle", "mfi_14", "rsi_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["mfi_14"] < self.p.mfi_max)
                & (df["rsi_14"] < self.p.rsi_max) & (F.atr_regime(df) <= self.p.max_atr_regime))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
