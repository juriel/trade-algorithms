"""Algoritmo 03c_v2 - Rebote Bollinger+MFI con stop fijo y bandas anchas

Mejora de 03c. Análisis: con bandas estrechas (ancho < 9%) el retorno por operación era 0.46% contra 1.6% en
bandas anchas. Cambios: exige ancho de banda mínimo, añade stop fijo y acorta el tiempo máximo.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P03cV2(Params):
    target_pct: Optional[float] = 0.05
    max_hold_days: Optional[int] = 8
    stop_pct: Optional[float] = 0.06
    mfi_max: float = 20.0
    min_bb_width: float = 10.0


class Algorithm03cV2(Algorithm):
    name = "algorithm03c_v2"
    description = "Rebote Bollinger+MFI con stop fijo y bandas anchas"
    params_cls = P03cV2
    requires = ["bb_lower", "bb_middle", "mfi_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["mfi_14"] < self.p.mfi_max)
                & ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100 >= self.p.min_bb_width))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
