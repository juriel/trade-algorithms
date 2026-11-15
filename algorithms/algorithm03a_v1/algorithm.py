"""Algoritmo 03a_v1 - Bollinger+RSI con salidas adaptativas al ATR

Mejora de 03a. Análisis: 25% de operaciones por tiempo con -7.2% de media; el retorno crece con el ATR%
(0.43% en el cuartil bajo, 1.34% en el alto). Cambios: filtro de ATR% y meta/stop en múltiplos de ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P03aV1(Params):
    target_pct: Optional[float] = 0.04
    max_hold_days: Optional[int] = 10
    stop_pct: Optional[float] = None
    rsi_max: float = 30.0
    min_atr_pct: float = 2.0
    target_atr_mult: Optional[float] = 1.5
    stop_atr_mult: Optional[float] = 2.5


class Algorithm03aV1(Algorithm):
    name = "algorithm03a_v1"
    description = "Bollinger+RSI con salidas adaptativas al ATR"
    params_cls = P03aV1
    requires = ["bb_lower", "bb_middle", "rsi_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["rsi_14"] < self.p.rsi_max)
                & (df["atr_14"] / df["close"] * 100 >= self.p.min_atr_pct))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
