"""Algoritmo creative02 - Giro del pico del VIX

Idea: de mercado, no de la acción. Tras un pico de miedo (VIX en su percentil alto del año en los últimos 5 días) el
primer día en que el VIX baja suele marcar el rebote general. Se compran acciones que aún están débiles (RSI bajo)
y sobre su SMA200; se sale cuando el VIX se normaliza (bajo `exit_pctrank`), por meta/stop de ATR o por tiempo.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class PCreative02(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = 8
    stop_pct: Optional[float] = None
    spike_pctrank: float = 85.0
    rsi_max: float = 50.0
    exit_pctrank: float = 50.0
    target_atr_mult: Optional[float] = 2.5
    stop_atr_mult: Optional[float] = 3.0


class AlgorithmCreative02(Algorithm):
    name = "algorithmcreative02"
    description = "Giro del pico del VIX"
    params_cls = PCreative02
    requires = ["mkt_vix", "mkt_vix_pctrank", "rsi_14", "sma_200", "atr_14"]

    def buy_signal(self, df):
        spike = df["mkt_vix_pctrank"].rolling(5).max() >= self.p.spike_pctrank
        turning = df["mkt_vix"] < df["mkt_vix"].shift(1)
        return spike & turning & (df["rsi_14"] < self.p.rsi_max) & (df["close"] > df["sma_200"])

    def sell_signal(self, df):
        return df["mkt_vix_pctrank"] <= self.p.exit_pctrank
