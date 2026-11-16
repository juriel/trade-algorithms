"""Algoritmo aictl03 - control aleatorio sobre 03a_v2_r2_i2.

CONTROL de algorithmai03: deja pasar cada señal de algorithm03a_v2_r2_i2 al azar (determinista) con probabilidad `keep_frac`,
igual a la fracción que deja pasar el modelo en el diagnóstico fuera de muestra. Si el modelo no supera a este control, no aporta.
"""
from dataclasses import dataclass

from algorithms.ml import random_gate
from algorithms.algorithm03a_v2_r2_i2.algorithm import Algorithm03aV2r2I2, P03aV2r2I2


@dataclass
class PAICTL03(P03aV2r2I2):
    keep_frac: float = 0.59


class AlgorithmAICTL03(Algorithm03aV2r2I2):
    name = "algorithmaictl03"
    description = "control aleatorio sobre 03a_v2_r2_i2"
    params_cls = PAICTL03

    def buy_signal(self, df):
        return random_gate(df, super().buy_signal(df), self.p.keep_frac)
