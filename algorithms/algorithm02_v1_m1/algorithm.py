"""Algoritmo 02_v1_m1 - 02_v1 solo en régimen alcista sano.

Observación: las tendencias rinden menos con la curva de tasas invertida (3.6% por operación contra ~8-11%) y mejor
con amplitud alta. Solo compra con el S&P 500 sobre su SMA200, amplitud suficiente y curva no invertida.
Base: algorithm02_v1 (mismas reglas de entrada/salida; este filtro de mercado se suma a la entrada).
Requiere la BD con datos de mercado (ticker2db.update_market). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm02_v1.algorithm import Algorithm02V1, P02V1


@dataclass
class P02V1M1(P02V1):
    min_breadth: float = 45.0
    min_curve: float = 0.7


class Algorithm02V1M1(Algorithm02V1):
    name = "algorithm02_v1_m1"
    description = "02_v1 solo en régimen alcista sano"
    params_cls = P02V1M1
    requires = list(Algorithm02V1.requires) + ['mkt_spx_above_sma200', 'mkt_breadth200', 'mkt_curve']

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.healthy_bull(df, self.p.min_breadth, self.p.min_curve))
