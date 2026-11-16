"""Algoritmo 01b_i2 - 01b más tamaño con IBS muy bajo.

Misma entrada que 01b; la posición es `boost` veces más grande cuando el IBS de ayer es <= `ibs_boost_max` (cierre pegado al mínimo
del día), donde la señal rindió más. Solo tiene efecto en el motor de carteras.
Base: algorithm01b (copia de sus reglas por herencia; esta variación solo añade lo descrito). Variables en variables.cfg.
"""
from dataclasses import dataclass

import pandas as pd

from algorithms import features as F
from algorithms.algorithm01b.algorithm import Algorithm01b, Params01b


@dataclass
class P01bI2(Params01b):
    ibs_boost_max: float = 0.07
    boost: float = 1.5


class Algorithm01bI2(Algorithm01b):
    name = "algorithm01b_i2"
    description = "01b más tamaño con IBS muy bajo"
    params_cls = P01bI2


    def size_series(self, df):
        return pd.Series(1.0, index=df.index).where(~(F.ibs(df) <= self.p.ibs_boost_max), self.p.boost)
