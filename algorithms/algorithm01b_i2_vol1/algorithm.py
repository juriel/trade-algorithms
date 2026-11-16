"""Algoritmo 01b_i2_vol1 - 01b_i2 solo con volumen tranquilo.

Estudio de eventos (volume_study.py): en las estrategias de caída el rebote fue mayor con volumen normal que con volumen
climático (tercil bajo menos alto: +0,9 a +1,1 puntos por operación en descubrimiento; mismo signo, pero sin significancia, en
las muestras de confirmación). Solo compra si el volumen del día de la señal no se salió del promedio.
Base: algorithm01b_i2 (copia de sus reglas por herencia). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm01b_i2.algorithm import Algorithm01bI2, P01bI2


@dataclass
class P01bi2VOL1(P01bI2):
    max_vol_ratio: float = 1.5


class Algorithm01bi2VOL1(Algorithm01bI2):
    name = "algorithm01b_i2_vol1"
    description = "01b_i2 solo con volumen tranquilo"
    params_cls = P01bi2VOL1
    requires = list(Algorithm01bI2.requires) + ["volume"]

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.volume_ratio(df) <= self.p.max_vol_ratio)
