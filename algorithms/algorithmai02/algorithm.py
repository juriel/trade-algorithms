"""Algoritmo ai02 - IA (meta-etiquetado) sobre 03a_v1_i2.

Meta-etiquetado con gradient boosting sobre algorithm03a_v1_i2: el modelo anual (entrenado solo con operaciones terminadas antes del 1 de enero,
acciones del grupo 'análisis') estima P(ganar) de cada señal y la deja pasar si supera la tasa histórica + `margin`.
Sin modelo (antes de 2006) no opera. Ver algorithms/ml.py.
"""
from dataclasses import dataclass

from algorithms.ml import RAW_COLS, MetaGate
from algorithms.algorithm03a_v1_i2.algorithm import Algorithm03aV1I2, P03aV1I2


@dataclass
class PAI02(P03aV1I2):
    margin: float = 0.0


class AlgorithmAI02(Algorithm03aV1I2):
    name = "algorithmai02"
    description = "IA sobre 03a_v1_i2"
    params_cls = PAI02
    requires = list(dict.fromkeys(list(Algorithm03aV1I2.requires) + RAW_COLS))

    def buy_signal(self, df):
        return MetaGate("algorithm03a_v1_i2", self.p.margin).gate(df, super().buy_signal(df))
