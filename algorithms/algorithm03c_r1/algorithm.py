"""Algoritmo 03c_r1 - Bollinger+MFI con RSI(2) y tendencia (estilo Connors)

Base 03c. Compra el retroceso solo a favor de la tendencia de largo plazo (cierre > SMA200), con RSI(2) < 10 y MFI\nbajo; sale al superar la media de 5 días, con stop de 6% y máximo de 5 días.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class P03cR1(Params):
    target_pct: Optional[float] = 0.05
    max_hold_days: Optional[int] = 5
    stop_pct: Optional[float] = 0.06
    mfi_max: float = 30.0
    rsi2_max: float = 10.0
    exit_sma: int = 5


class Algorithm03cR1(Algorithm):
    name = "algorithm03c_r1"
    description = "Bollinger+MFI con RSI(2) y tendencia (estilo Connors)"
    params_cls = P03cR1
    requires = ["bb_lower", "sma_200", "mfi_14"]

    def buy_signal(self, df):
        return ((df["close"] < df["bb_lower"]) & (df["close"] > df["sma_200"])
                & (df["mfi_14"] < self.p.mfi_max) & (F.rsi(df, 2) < self.p.rsi2_max))

    def sell_signal(self, df):
        return df["close"] > F.sma(df, self.p.exit_sma)
