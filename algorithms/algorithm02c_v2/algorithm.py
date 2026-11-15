"""Algoritmo 02c_v2 - Retroceso en tendencia con volatilidad, MACD negativo y stop fijo

Mejora de 02c. Análisis: ATR% alto (>2.9) rinde el doble que el bajo y el MACD más negativo (retroceso
más fuerte) rinde 1.27% frente a ~0.5%. Cambios: ATR% mínimo, MACD bajo, stop fijo y salida más corta.
Las variables se editan en variables.cfg (los valores de aquí son de respaldo).
"""
from dataclasses import dataclass
from typing import Optional

from algorithms.engine import Algorithm, Params


@dataclass
class P02cV2(Params):
    target_pct: Optional[float] = 0.07
    max_hold_days: Optional[int] = 10
    stop_pct: Optional[float] = 0.06
    rsi_max: float = 50.0
    rsi_sell: float = 70.0
    min_atr_pct: float = 2.0
    max_macd_pct: float = -0.3


class Algorithm02cV2(Algorithm):
    name = "algorithm02c_v2"
    description = "Retroceso en tendencia con volatilidad, MACD negativo y stop fijo"
    params_cls = P02cV2
    requires = ["sma_20", "sma_50", "sma_200", "rsi_14", "macd_hist", "atr_14"]

    def buy_signal(self, df):
        return ((df["sma_50"] > df["sma_200"]) & (df["close"] > df["sma_200"]) & (df["close"] < df["sma_20"])
                & (df["rsi_14"] < self.p.rsi_max) & (df["atr_14"] / df["close"] * 100 >= self.p.min_atr_pct)
                & (df["macd_hist"] / df["close"] * 100 <= self.p.max_macd_pct))

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
