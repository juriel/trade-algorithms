"""Algoritmo aictl02 - control aleatorio sobre 03a_v1_i2.

CONTROL de algorithmai02: deja pasar cada señal de algorithm03a_v1_i2 al azar (determinista) con probabilidad `keep_frac`,
igual a la fracción que deja pasar el modelo en el diagnóstico fuera de muestra. Si el modelo no supera a este control, no aporta.
"""
from dataclasses import dataclass

from algorithms.ml import random_gate
from algorithms.algorithm03a_v1_i2.algorithm import Algorithm03aV1I2, P03aV1I2


@dataclass
class PAICTL02(P03aV1I2):
    keep_frac: float = 0.62


class AlgorithmAICTL02(Algorithm03aV1I2):
    name = "algorithmaictl02"
    description = "control aleatorio sobre 03a_v1_i2"
    params_cls = PAICTL02

    def buy_signal(self, df):
        return random_gate(df, super().buy_signal(df), self.p.keep_frac)
