"""Algoritmo 01b_i2_vol2 - 01b_i2 solo con volumen secándose.

Variante del anterior: en vez del volumen de un día, exige que el volumen de los últimos 5 días no esté por encima del normal
(la presión vendedora se agota). Evidencia aún más débil en el estudio de eventos.
Base: algorithm01b_i2 (copia de sus reglas por herencia). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm01b_i2.algorithm import Algorithm01bI2, P01bI2


@dataclass
class P01bi2VOL2(P01bI2):
    max_vol_dryup: float = 1.3


class Algorithm01bi2VOL2(Algorithm01bI2):
    name = "algorithm01b_i2_vol2"
    description = "01b_i2 solo con volumen secándose"
    params_cls = P01bi2VOL2
    requires = list(Algorithm01bI2.requires) + ["volume"]

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.volume_dryup(df, 5, 20) <= self.p.max_vol_dryup)
