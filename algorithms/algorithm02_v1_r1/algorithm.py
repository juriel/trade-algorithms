"""Algoritmo 02_v1_r1 - Tendencia con Chandelier clásico (máximos) y stop inicial por ATR

Base 02_v1. El Chandelier de LeBeau/Elder cuelga del MÁXIMO (high) más alto, no del cierre más alto, y se añade un stop\ninicial por ATR para limitar la pérdida antes de que el trailing se active.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P02V1R1(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    adx_min: float = 20.0
    min_macd_pct: float = 0.5
    chandelier_window: int = 22
    chandelier_k: float = 5.0
    stop_atr_mult: Optional[float] = 4.0


class Algorithm02V1R1(Algorithm):
    name = "algorithm02_v1_r1"
    description = "Tendencia con Chandelier clásico (máximos) y stop inicial por ATR"
    params_cls = P02V1R1
    requires = ["sma_20", "sma_50", "sma_200", "adx_14", "macd_hist", "atr_14"]

    def buy_signal(self, df):
        return ((df["sma_20"] > df["sma_50"]) & (df["close"] > df["sma_200"]) & (df["adx_14"] > self.p.adx_min)
                & (df["macd_hist"] / df["close"] * 100 >= self.p.min_macd_pct))

    def sell_signal(self, df):
        return df["close"] < df["high"].rolling(self.p.chandelier_window).max() - self.p.chandelier_k * df["atr_14"]
