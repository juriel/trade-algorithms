"""Algoritmo 03c_v2_r1 - Bollinger+MFI con confirmación: reingreso a la banda

Base 03c_v2. En vez de comprar el cierre bajo la banda inferior (cuchillo cayendo), espera a que el precio\nvuelva a cerrar DENTRO de la banda tras un cierre fuera con MFI bajo (confirmación de giro). Vende en la banda media; máx. 5 días.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03cV2R1(Params):
    target_pct: Optional[float] = 0.05
    max_hold_days: Optional[int] = 5
    stop_pct: Optional[float] = 0.06
    mfi_max: float = 20.0
    min_bb_width: float = 10.0


class Algorithm03cV2R1(Algorithm):
    name = "algorithm03c_v2_r1"
    description = "Bollinger+MFI con confirmación: reingreso a la banda"
    params_cls = P03cV2R1
    requires = ["bb_lower", "bb_middle", "bb_upper", "mfi_14"]

    def buy_signal(self, df):
        return (F.back_inside_lower(df) & (df["mfi_14"].shift(1) < self.p.mfi_max)
                & (F.bb_width(df).shift(1) >= self.p.min_bb_width))

    def sell_signal(self, df):
        return df["close"] >= df["bb_middle"]
