"""Algoritmo 03c_v1_m2 - 03c_v1 solo con estrés en expansión.

Observación: los mejores rebotes ocurren con VIX sobre su media de 50 días (x1.3 o más), crédito riesgoso
(HYG/LQD) cayendo >4% o S&P 500 en caída fuerte. Versión menos restrictiva que _m1: basta una señal.
Base: algorithm03c_v1 (mismas reglas de entrada/salida; este filtro de mercado se suma a la entrada).
Requiere la BD con datos de mercado (ticker2db.update_market). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm03c_v1.algorithm import Algorithm03cV1, P03cV1


@dataclass
class P03cV1M2(P03cV1):
    vix_ratio50_min: float = 1.3
    credit_ret20_max: float = -4.0
    spx_ret20_max: float = -8.0


class Algorithm03cV1M2(Algorithm03cV1):
    name = "algorithm03c_v1_m2"
    description = "03c_v1 solo con estrés en expansión"
    params_cls = P03cV1M2
    requires = list(Algorithm03cV1.requires) + ['mkt_vix_ratio50', 'mkt_credit_ret20', 'mkt_spx_ret20']

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.stress_expansion(df, self.p.vix_ratio50_min, self.p.credit_ret20_max, self.p.spx_ret20_max))
