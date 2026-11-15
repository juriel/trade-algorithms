"""Algoritmo 03 - Retorno a la media con Bandas de Bollinger + Estocástico.

COMPRA (apertura): ayer el cierre quedó bajo la banda inferior y %K < `stoch_max`.
VENTA: meta +`target_pct`, o a la apertura si ayer el cierre alcanzó la banda
       media, o tras `max_hold_days` días.
"""
from dataclasses import dataclass

from algorithms.engine import Algorithm, Params


@dataclass
class Params03(Params):
    # Valores por defecto de respaldo; los valores reales se editan en variables.cfg
    stoch_max: float = 20.0
    exit_at_middle_band: bool = True
    target_pct: float = 0.04
    max_hold_days: int = 15


class Algorithm03(Algorithm):
    name = "algorithm03"
    description = "Retorno a la media: cierre bajo Bollinger inferior y Stoch bajo"
    params_cls = Params03
    requires = ["bb_lower", "bb_middle", "stoch_k"]

    def buy_signal(self, df):
        return (df["close"] < df["bb_lower"]) & (df["stoch_k"] < self.p.stoch_max)

    def sell_signal(self, df):
        if self.p.exit_at_middle_band:
            return df["close"] >= df["bb_middle"]
        return super().sell_signal(df)
