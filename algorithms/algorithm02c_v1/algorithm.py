"""Algoritmo 02c_v1 - Retroceso en tendencia con ADX, pullback profundo y salidas ATR

Mejora de 02c. Análisis: 63% de las operaciones salían por tiempo con -2.4% de media; el ADX alto (>27) rinde
el doble que el bajo y los retrocesos más profundos bajo la SMA20 rinden más. Cambios: ADX mínimo, pullback
mínimo y meta/stop en múltiplos de ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P02cV1(Params):
    target_pct: Optional[float] = 0.06
    max_hold_days: Optional[int] = 12
    stop_pct: Optional[float] = None
    rsi_max: float = 50.0
    rsi_sell: float = 70.0
    adx_min: float = 25.0
    max_dist_sma20: float = -1.5
    target_atr_mult: Optional[float] = 2.0
    stop_atr_mult: Optional[float] = 2.5


class Algorithm02cV1(Algorithm):
    name = "algorithm02c_v1"
    description = "Retroceso en tendencia con ADX, pullback profundo y salidas ATR"
    params_cls = P02cV1
    requires = ["sma_20", "sma_50", "sma_200", "rsi_14", "adx_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["sma_50"] > df["sma_200"]) & (df["close"] > df["sma_200"]) & (df["close"] < df["sma_20"])
                & (df["rsi_14"] < self.p.rsi_max) & (df["adx_14"] >= self.p.adx_min)
                & ((df["close"] / df["sma_20"] - 1) * 100 <= self.p.max_dist_sma20))

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
