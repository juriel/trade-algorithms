"""Algoritmo creative05 - Interruptor macro risk-on/risk-off sobre tendencia

Idea: la tendencia de una acción funciona mejor con viento macro a favor. Régimen 'risk-on' = S&P 500 sobre su SMA200,
VIX no en expansión (VIX/media50 bajo), dólar sin avance fuerte (DXY a 20 días) y curva de tasas no invertida. Se compra
la tendencia (EMA12 > EMA26, sobre SMA50, ADX) solo en risk-on y se vende a la apertura cuando el régimen pasa a risk-off.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class PCreative05(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    adx_min: float = 18.0
    max_vix_ratio: float = 1.1
    max_dxy_ret20: float = 1.5
    min_curve: float = 0.0
    riskoff_vix_ratio: float = 1.3
    stop_atr_mult: Optional[float] = 4.0


class AlgorithmCreative05(Algorithm):
    name = "algorithmcreative05"
    description = "Interruptor macro risk-on/risk-off sobre tendencia"
    params_cls = PCreative05
    requires = ["mkt_spx_above_sma200", "mkt_vix_ratio50", "mkt_dxy_ret20", "mkt_curve", "ema_12", "ema_26", "sma_50", "adx_14", "atr_14"]

    def buy_signal(self, df):
        risk_on = ((df["mkt_spx_above_sma200"] == 1) & (df["mkt_vix_ratio50"] < self.p.max_vix_ratio)
                   & (df["mkt_dxy_ret20"] < self.p.max_dxy_ret20) & (df["mkt_curve"] >= self.p.min_curve))
        trend = (df["ema_12"] > df["ema_26"]) & (df["close"] > df["sma_50"]) & (df["adx_14"] > self.p.adx_min)
        return risk_on & trend

    def sell_signal(self, df):
        return (df["mkt_spx_above_sma200"] == 0) | (df["mkt_vix_ratio50"] >= self.p.riskoff_vix_ratio)
