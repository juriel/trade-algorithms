"""Algoritmo 02_v1_m2 - 02_v1 régimen alcista sano, sin estrés ni dólar al alza.

Como _m1 y además evita VIX en su percentil alto (> max_vix_pctrank) y avances fuertes del dólar (DXY a 20 días >
max_dxy_ret20).
Base: algorithm02_v1 (mismas reglas de entrada/salida; este filtro de mercado se suma a la entrada).
Requiere la BD con datos de mercado (ticker2db.update_market). Variables en variables.cfg.
"""
from dataclasses import dataclass

from algorithms import features as F
from algorithms.algorithm02_v1.algorithm import Algorithm02V1, P02V1


@dataclass
class P02V1M2(P02V1):
    min_breadth: float = 45.0
    min_curve: float = 0.7
    max_vix_pctrank: float = 80.0
    max_dxy_ret20: float = 1.3


class Algorithm02V1M2(Algorithm02V1):
    name = "algorithm02_v1_m2"
    description = "02_v1 régimen alcista sano, sin estrés ni dólar al alza"
    params_cls = P02V1M2
    requires = list(Algorithm02V1.requires) + ['mkt_spx_above_sma200', 'mkt_breadth200', 'mkt_curve', 'mkt_dxy_ret20', 'mkt_vix_pctrank']

    def buy_signal(self, df):
        return super().buy_signal(df) & (F.healthy_bull(df, self.p.min_breadth, self.p.min_curve) & (df["mkt_vix_pctrank"] <= self.p.max_vix_pctrank) & (df["mkt_dxy_ret20"] <= self.p.max_dxy_ret20))
