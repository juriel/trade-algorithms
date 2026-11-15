"""Algoritmo creative03 - Compresión de volatilidad y ruptura con volumen

Idea: tras un periodo de volatilidad comprimida (ancho de Bollinger en su cuantil bajo de los últimos 120 días en algún
día de los últimos 5), una ruptura sobre la banda superior con volumen alto y a favor de la SMA200 suele iniciar
un movimiento fuerte. Sin meta: trailing Chandelier amplio y stop inicial por ATR.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms import features as F
from algorithms.engine import Algorithm, Params


@dataclass
class PCreative03(Params):
    target_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    stop_pct: Optional[float] = None
    squeeze_quantile: float = 0.2
    squeeze_lookback: int = 5
    vol_mult: float = 1.5
    chandelier_window: int = 22
    chandelier_k: float = 4.0
    stop_atr_mult: Optional[float] = 3.0


class AlgorithmCreative03(Algorithm):
    name = "algorithmcreative03"
    description = "Compresión de volatilidad y ruptura con volumen"
    params_cls = PCreative03
    requires = ["bb_upper", "bb_lower", "bb_middle", "volume", "sma_200", "atr_14"]

    def buy_signal(self, df):
        w = F.bb_width(df)
        squeezed = (w <= w.rolling(120).quantile(self.p.squeeze_quantile)).rolling(self.p.squeeze_lookback).max() > 0
        breakout = (df["close"] > df["bb_upper"]) & (df["close"] > df["sma_200"])
        return squeezed & breakout & (F.volume_ratio(df) >= self.p.vol_mult)

    def sell_signal(self, df):
        return df["close"] < df["close"].rolling(self.p.chandelier_window).max() - self.p.chandelier_k * df["atr_14"]
