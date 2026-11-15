"""Algoritmo 01 - Rebote por sobreventa (RSI) a favor de la tendencia grande.

COMPRA (apertura): el RSI(14) de ayer < `rsi_buy` y, si `use_trend_filter`,
                   el cierre de ayer está sobre la SMA 200.
VENTA: meta +`target_pct`, o a la apertura si el RSI de ayer > `rsi_sell`,
       o tras `max_hold_days` días.
"""
from dataclasses import dataclass

from algorithms.engine import Algorithm, Params


@dataclass
class Params01(Params):
    # Valores por defecto de respaldo; los valores reales se editan en variables.cfg
    rsi_buy: float = 30.0
    rsi_sell: float = 70.0
    use_trend_filter: bool = True
    target_pct: float = 0.05
    max_hold_days: int = 10


class Algorithm01(Algorithm):
    name = "algorithm01"
    description = "Rebote por sobreventa RSI con filtro SMA200"
    params_cls = Params01
    requires = ["rsi_14", "sma_200"]

    def buy_signal(self, df):
        sig = df["rsi_14"] < self.p.rsi_buy
        if self.p.use_trend_filter:
            sig &= df["close"] > df["sma_200"]
        return sig

    def sell_signal(self, df):
        return df["rsi_14"] > self.p.rsi_sell
