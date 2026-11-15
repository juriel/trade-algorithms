"""Algoritmo 03c_v1_m1 - 03c_v1 solo en capitulación del mercado.

Observación (análisis 1996-2019, mitad 'análisis'): los rebotes rinden más cuando el mercado está en
capitulación (VIX en su percentil >96 del año, RSI del S&P 500 < 31, amplitud < 25%, S&P -8% a 20 días).
Solo compra si al menos `min_stress_score` de esas 4 señales están activas.
Base: algorithm03c_v1 (mismas reglas de entrada/salida; este filtro de mercado se suma a la entrada).
Requiere la BD con datos de mercado (ticker2db.update_market). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm03c_v1.algorithm import Algorithm03cV1, P03cV1


@dataclass
class P03cV1M1(P03cV1):
    vix_pctrank_min: float = 90.0
    spx_rsi_max: float = 31.0
    breadth_max: float = 25.0
    spx_ret20_max: float = -8.0
    min_stress_score: int = 2


class Algorithm03cV1M1(Algorithm03cV1):
    name = "algorithm03c_v1_m1"
    description = "03c_v1 solo en capitulación del mercado"
    params_cls = P03cV1M1
    requires = list(Algorithm03cV1.requires) + ['mkt_vix_pctrank', 'mkt_spx_rsi14', 'mkt_breadth200', 'mkt_spx_ret20']

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.stress_score(df, self.p.vix_pctrank_min, self.p.spx_rsi_max, self.p.breadth_max, self.p.spx_ret20_max) >= self.p.min_stress_score)
