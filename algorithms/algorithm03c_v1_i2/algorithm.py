"""Algoritmo 03c_v1_i2 - 03c_v1 tamaño de posición proporcional a la profundidad.

Misma entrada que la base (no descarta señales) pero el tamaño de la posición crece con la caída a 5 días: un retroceso de
`size_ref_drop` % usa el tamaño normal, uno el doble de profundo el doble, acotado entre `size_min` y `size_max` veces.
Idea: concentrar capital donde el rebote esperado es mayor. Solo tiene efecto en el motor de carteras.
Base: algorithm03c_v1 (copia de sus reglas por herencia; esta variación solo añade lo descrito). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm03c_v1.algorithm import Algorithm03cV1, P03cV1


@dataclass
class P03cV1I2(P03cV1):
    size_ref_drop: float = 10.0
    size_min: float = 0.5
    size_max: float = 3.0


class Algorithm03cV1I2(Algorithm03cV1):
    name = "algorithm03c_v1_i2"
    description = "03c_v1 tamaño de posición proporcional a la profundidad"
    params_cls = P03cV1I2


    def size_series(self, df):
        return (-F.ret_n(df, 5) / self.p.size_ref_drop).clip(lower=self.p.size_min, upper=self.p.size_max)
