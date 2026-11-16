"""Algoritmo aictl01 - control aleatorio sobre 01b_i2.

CONTROL de algorithmai01: deja pasar cada señal de algorithm01b_i2 al azar (determinista) con probabilidad `keep_frac`,
igual a la fracción que deja pasar el modelo en el diagnóstico fuera de muestra. Si el modelo no supera a este control, no aporta.
"""
from dataclasses import dataclass

from algorithms.ml import random_gate
from algorithms.algorithm01b_i2.algorithm import Algorithm01bI2, P01bI2


@dataclass
class PAICTL01(P01bI2):
    keep_frac: float = 0.57


class AlgorithmAICTL01(Algorithm01bI2):
    name = "algorithmaictl01"
    description = "control aleatorio sobre 01b_i2"
    params_cls = PAICTL01

    def buy_signal(self, df):
        return random_gate(df, super().buy_signal(df), self.p.keep_frac)
