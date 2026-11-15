"""Algoritmo 02_v1 - Tendencia con salida Chandelier y momentum MACD

Mejora de 02. Análisis: 75% de las operaciones salían por la SMA50 con -3.5% de media (salida tardía) y la meta
fija de 15% recortaba las ganancias; el cuartil de mayor MACD% rinde el doble. Cambios: exige momentum
MACD mínimo, sustituye la salida por un trailing Chandelier amplio (máximo de N días - k*ATR) y quita la meta
(dejar correr las ganancias). Con k=3 el trailing cortaba demasiado pronto; k=5 resultó mejor en el análisis.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P02V1(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    adx_min: float = 20.0
    min_macd_pct: float = 0.5
    chandelier_window: int = 22
    chandelier_k: float = 5.0


class Algorithm02V1(Algorithm):
    name = "algorithm02_v1"
    description = "Tendencia con salida Chandelier y momentum MACD"
    params_cls = P02V1
    requires = ["sma_20", "sma_50", "sma_200", "adx_14", "macd_hist", "atr_14"]

    def buy_signal(self, df):
        return ((df["sma_20"] > df["sma_50"]) & (df["close"] > df["sma_200"]) & (df["adx_14"] > self.p.adx_min)
                & (df["macd_hist"] / df["close"] * 100 >= self.p.min_macd_pct))

    def sell_signal(self, df):
        return df["close"] < df["close"].rolling(self.p.chandelier_window).max() - self.p.chandelier_k * df["atr_14"]
