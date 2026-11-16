"""Algoritmo ai01 - IA (meta-etiquetado) sobre 01b_i2.

Meta-etiquetado con gradient boosting sobre algorithm01b_i2: el modelo anual (entrenado solo con operaciones terminadas antes del 1 de enero,
acciones del grupo 'análisis') estima P(ganar) de cada señal y la deja pasar si supera la tasa histórica + `margin`.
Sin modelo (antes de 2006) no opera. Ver algorithms/ml.py.
"""
from dataclasses import dataclass

from algorithms.ml import RAW_COLS, MetaGate
from algorithms.algorithm01b_i2.algorithm import Algorithm01bI2, P01bI2


@dataclass
class PAI01(P01bI2):
    margin: float = 0.0


class AlgorithmAI01(Algorithm01bI2):
    name = "algorithmai01"
    description = "IA sobre 01b_i2"
    params_cls = PAI01
    requires = list(dict.fromkeys(list(Algorithm01bI2.requires) + RAW_COLS))

    def buy_signal(self, df):
        return MetaGate("algorithm01b_i2", self.p.margin).gate(df, super().buy_signal(df))
