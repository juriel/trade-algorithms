"""Algoritmo 01b_i1 - 01b IBS bajo y sin cuchillos cayendo.

Observación: en 01b la señal es casi uniforme, pero rinde más con IBS <= 0,07 (0,89% contra ~0,55%) y mucho peor cuando la acción
está a más de 33% de su máximo anual (0,23%). Exige IBS bajo y una distancia a máximos intermedia.
Base: algorithm01b (copia de sus reglas por herencia; esta variación solo añade lo descrito). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm01b.algorithm import Algorithm01b, Params01b


@dataclass
class P01bI1(Params01b):
    ibs_max: float = 0.1
    min_dist_high: float = -35.0
    max_dist_high: float = -10.0


class Algorithm01bI1(Algorithm01b):
    name = "algorithm01b_i1"
    description = "01b IBS bajo y sin cuchillos cayendo"
    params_cls = P01bI1

    def buy_signal(self, df):
        d = F.dist_high(df, 252)
        return super().buy_signal(df) & (F.ibs(df) <= self.p.ibs_max) & (d >= self.p.min_dist_high) & (d <= self.p.max_dist_high)
