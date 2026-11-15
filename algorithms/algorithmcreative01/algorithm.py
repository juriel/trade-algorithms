"""Algoritmo creative01 - Clímax vendedor con vela de rechazo

Idea: el final de una caída suele marcarse con un 'clímax': volumen muy superior al normal en un día de caída fuerte
y, enseguida, una vela que rechaza los mínimos (martillo, envolvente alcista, línea penetrante, estrella de la mañana,
palomo o cierre lejos del mínimo del día, IBS alto). Se compra el rebote y se sale al volver a la SMA20.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class PCreative01(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = 6
    stop_pct: Optional[float] = None
    vol_mult: float = 2.0
    min_drop_pct: float = 3.0
    ibs_min: float = 0.5
    target_atr_mult: Optional[float] = 2.0
    stop_atr_mult: Optional[float] = 2.5


class AlgorithmCreative01(Algorithm):
    name = "algorithmcreative01"
    description = "Clímax vendedor con vela de rechazo"
    params_cls = PCreative01
    requires = ["volume", "sma_20", "atr_14", "cdl_hammer", "cdl_engulfing", "cdl_piercing", "cdl_morningstar", "cdl_homingpigeon"]

    def buy_signal(self, df):
        drop = (df["close"] / df["close"].shift(1) - 1) * 100 <= -self.p.min_drop_pct
        candle = ((df["cdl_hammer"] > 0) | (df["cdl_engulfing"] > 0) | (df["cdl_piercing"] > 0)
                  | (df["cdl_morningstar"] > 0) | (df["cdl_homingpigeon"] > 0) | (F.ibs(df) >= self.p.ibs_min))
        return (F.volume_ratio(df) >= self.p.vol_mult) & drop & candle

    def sell_signal(self, df):
        return df["close"] >= df["sma_20"]
