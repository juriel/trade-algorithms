"""Algoritmo creative06 - Efecto fin de mes (turn-of-the-month)

Idea: anomalía de calendario documentada en la literatura: las acciones tienden a rendir más alrededor del cambio de
mes (último día hábil y primeros días del siguiente). Se compra a la apertura del último día hábil del mes (la señal
es el penúltimo, calendario conocido de antemano) y se mantiene `max_hold_days` días. Solo con el S&P 500 y la
acción sobre su SMA200. Sin otras reglas: es la prueba del efecto de calendario.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class PCreative06(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = 4
    stop_pct: Optional[float] = None
    days_left: int = 1
    use_market_filter: bool = True


class AlgorithmCreative06(Algorithm):
    name = "algorithmcreative06"
    description = "Efecto fin de mes (turn-of-the-month)"
    params_cls = PCreative06
    requires = ["mkt_spx_above_sma200", "sma_200"]

    def buy_signal(self, df):
        sig = (F.business_days_left(df) == self.p.days_left) & (df["close"] > df["sma_200"])
        if self.p.use_market_filter:
            sig &= df["mkt_spx_above_sma200"] == 1
        return sig

    def sell_signal(self, df):
        return super().sell_signal(df)  # sin señal de venta: solo por tiempo (max_hold_days)
