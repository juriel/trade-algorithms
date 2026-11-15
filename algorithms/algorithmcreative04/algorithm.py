"""Algoritmo creative04 - Líderes del mercado en retroceso

Idea: las acciones con fuerza relativa alta (retorno de 120 días muy superior al del S&P 500) tienden a seguir
liderando. Se compran cuando retroceden (bajo la SMA20, RSI bajo) dentro de su tendencia alcista y con el
S&P 500 sobre su SMA200. Sale por RSI alto, meta/stop de ATR o tiempo.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class PCreative04(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = 15
    stop_pct: Optional[float] = None
    min_rel_strength: float = 10.0
    rsi_max: float = 45.0
    rsi_sell: float = 65.0
    target_atr_mult: Optional[float] = 3.0
    stop_atr_mult: Optional[float] = 3.0


class AlgorithmCreative04(Algorithm):
    name = "algorithmcreative04"
    description = "Líderes del mercado en retroceso"
    params_cls = PCreative04
    requires = ["mkt_spx_ret120", "mkt_spx_above_sma200", "sma_20", "sma_50", "sma_200", "rsi_14", "atr_14"]

    def buy_signal(self, df):
        leader = F.rel_strength(df, 120) >= self.p.min_rel_strength
        uptrend = (df["close"] > df["sma_200"]) & (df["sma_50"] > df["sma_200"])
        dip = (df["close"] < df["sma_20"]) & (df["rsi_14"] < self.p.rsi_max)
        return leader & uptrend & dip & (df["mkt_spx_above_sma200"] == 1)

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
