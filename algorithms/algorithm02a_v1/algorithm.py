"""Algoritmo 02a_v1 - Cruce de EMAs con salida Chandelier amplia

Mejora de 02a. Análisis: 65% de las operaciones salían por el cruce de EMAs con -4.9% de media (la peor salida
de todas) y la meta de 12% recortaba ganancias. Cambios: misma entrada, pero la salida es un trailing
Chandelier amplio (máximo de N días - k*ATR) y sin meta. Con k=3 cortaba demasiado pronto; k=5 fue mejor.
min_macd_pct (None = desactivado) permite exigir momentum MACD; en el análisis no mejoró.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P02aV1(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    adx_min: float = 20.0
    min_macd_pct: Optional[float] = None
    chandelier_window: int = 22
    chandelier_k: float = 5.0


class Algorithm02aV1(Algorithm):
    name = "algorithm02a_v1"
    description = "Cruce de EMAs con salida Chandelier amplia"
    params_cls = P02aV1
    requires = ["ema_12", "ema_26", "sma_50", "adx_14", "macd_hist", "atr_14"]

    def buy_signal(self, df):
        sig = (df["ema_12"] > df["ema_26"]) & (df["close"] > df["sma_50"]) & (df["adx_14"] > self.p.adx_min)
        if self.p.min_macd_pct is not None:
            sig &= df["macd_hist"] / df["close"] * 100 >= self.p.min_macd_pct
        return sig

    def sell_signal(self, df):
        return df["close"] < df["close"].rolling(self.p.chandelier_window).max() - self.p.chandelier_k * df["atr_14"]
