"""Algoritmo 03c_v2_r2 - Bollinger+MFI con IBS

Base 03c_v2. Añade la condición IBS (Internal Bar Strength) <= ibs_max: el cierre quedó en el cuarto inferior del\nrango del día, señal de agotamiento vendedor. Vende en la banda media; máx. 5 días.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03cV2R2(Params):
    target_pct: Optional[float] = 0.05
    max_hold_days: Optional[int] = 5
    stop_pct: Optional[float] = 0.06
    mfi_max: float = 20.0
    min_bb_width: float = 10.0
    ibs_max: float = 0.25


class Algorithm03cV2R2(Algorithm):
    name = "algorithm03c_v2_r2"
    description = "Bollinger+MFI con IBS"
    params_cls = P03cV2R2
    requires = ["bb_lower", "bb_middle", "bb_upper", "mfi_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["mfi_14"] < self.p.mfi_max)
                & (F.ibs(df) <= self.p.ibs_max) & (F.bb_width(df) >= self.p.min_bb_width))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
