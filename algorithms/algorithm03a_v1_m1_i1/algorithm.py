"""Algoritmo 03a_v1_m1_i1 - 03a_v1_m1 solo caídas profundas.

Observación (análisis 1996-2019, mitad 'análisis'): en las cuatro estrategias de Bollinger el rebote crece con la profundidad
de la caída: ret. a 5 días <= -14% rinde 2,0-4,0% por operación contra 0,6-0,9% con caídas leves, y estar a >37% de los
máximos de 1 año rinde 1,9-3,7% contra 0,6-0,8% cerca de máximos. Solo compra cuando la caída es profunda.
Base: algorithm03a_v1_m1 (copia de sus reglas por herencia; esta variación solo añade lo descrito). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm03a_v1_m1.algorithm import Algorithm03aV1M1, P03aV1M1


@dataclass
class P03aV1m1I1(P03aV1M1):
    max_ret5: float = -10.0
    max_dist_high: float = -25.0


class Algorithm03aV1m1I1(Algorithm03aV1M1):
    name = "algorithm03a_v1_m1_i1"
    description = "03a_v1_m1 solo caídas profundas"
    params_cls = P03aV1m1I1

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.ret_n(df, 5) <= self.p.max_ret5) & (F.dist_high(df, 252) <= self.p.max_dist_high)
