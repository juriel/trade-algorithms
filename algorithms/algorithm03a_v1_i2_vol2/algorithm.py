"""Algoritmo 03a_v1_i2_vol2 - 03a_v1_i2 solo con volumen secándose.

Variante del anterior: en vez del volumen de un día, exige que el volumen de los últimos 5 días no esté por encima del normal
(la presión vendedora se agota). Evidencia aún más débil en el estudio de eventos.
Base: algorithm03a_v1_i2 (copia de sus reglas por herencia). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm03a_v1_i2.algorithm import Algorithm03aV1I2, P03aV1I2


@dataclass
class P03aV1i2VOL2(P03aV1I2):
    max_vol_dryup: float = 1.3


class Algorithm03aV1i2VOL2(Algorithm03aV1I2):
    name = "algorithm03a_v1_i2_vol2"
    description = "03a_v1_i2 solo con volumen secándose"
    params_cls = P03aV1i2VOL2
    requires = list(Algorithm03aV1I2.requires) + ["volume"]

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.volume_dryup(df, 5, 20) <= self.p.max_vol_dryup)
