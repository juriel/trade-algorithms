"""Algoritmo 03c_v1 - Rebote Bollinger+MFI con salidas adaptativas al ATR

Mejora de 03c. Análisis: el 27% de las operaciones salía por tiempo con -6.8% de media (sin límite de
pérdida) y la meta fija de 4-5% no se ajusta a la volatilidad (el cuartil de mayor ATR% rinde 3x el de menor).
Cambios: solo opera acciones con ATR% suficiente y la meta y el stop se miden en múltiplos de ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P03cV1(Params):
    target_pct: Optional[float] = 0.04
    max_hold_days: Optional[int] = 10
    stop_pct: Optional[float] = None
    mfi_max: float = 20.0
    min_atr_pct: float = 2.0
    target_atr_mult: Optional[float] = 1.5
    stop_atr_mult: Optional[float] = 2.5


class Algorithm03cV1(Algorithm):
    name = "algorithm03c_v1"
    description = "Rebote Bollinger+MFI con salidas adaptativas al ATR"
    params_cls = P03cV1
    requires = ["bb_lower", "bb_middle", "mfi_14", "atr_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["mfi_14"] < self.p.mfi_max)
                & (df["atr_14"] / df["close"] * 100 >= self.p.min_atr_pct))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
