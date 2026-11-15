"""Motor de backtest para algoritmos de inversión (solo largos, un símbolo).

Reglas del mercado simulado:
  * COMPRA: solo a la apertura del día (orden a mercado en la apertura).
    Puede estar condicionada por `Algorithm.buy_signal`.
  * VENTA: (a) a la apertura del día, por `Algorithm.sell_signal` o por haber
    alcanzado `max_hold_days`, o (b) al cumplir la meta `target_pct`
    (orden límite: se ejecuta al precio meta si el máximo del día lo alcanza,
    o a la apertura si esta ya lo supera).

Sin lookahead: las señales se calculan con datos al cierre del día t y el
motor las aplica en la apertura del día t+1.
"""
from __future__ import annotations

import ast
import configparser
import inspect
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

OHLC = ["open", "high", "low", "close"]


@dataclass
class Params:
    """Variables editables comunes a todos los algoritmos."""
    initial_capital: float = 10_000.0
    position_fraction: float = 1.0       # fracción del capital que se invierte en cada compra
    target_pct: Optional[float] = 0.05   # meta de venta (+5%); None = sin meta
    max_hold_days: Optional[int] = None  # vender a la apertura tras N barras; None = sin límite
    commission_pct: float = 0.0005       # comisión por operación (cada lado)
    slippage_pct: float = 0.0005         # deslizamiento en ejecuciones a mercado (aperturas)


def load_cfg(path, section: str = "params") -> dict:
    """Lee una sección (por defecto [params]) de un .cfg. Valores: números, True/False, None o texto."""
    cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=("#", ";"))
    cp.optionxform = str  # respeta mayúsculas/minúsculas
    cp.read(path, encoding="utf-8")
    out = {}
    for k, v in cp[section].items() if cp.has_section(section) else []:
        try:
            out[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            out[k] = v
    return out


class Algorithm:
    """Clase base. Subclases definen `params_cls`, `requires`, `buy_signal`, `sell_signal`."""
    name = "base"
    description = ""
    params_cls = Params
    requires: List[str] = []   # columnas de indicadores necesarias

    def __init__(self, cfg: Optional[str] = None, **overrides):
        """Prioridad: `overrides` > variables.cfg > valores por defecto del dataclass.

        `cfg` es la ruta a otro archivo de variables; por defecto se usa el
        `variables.cfg` que está junto al código del algoritmo (si existe).
        """
        path = Path(cfg) if cfg else Path(inspect.getfile(type(self))).with_name("variables.cfg")
        values = load_cfg(path) if path.exists() else {}
        values.update(overrides)
        unknown = set(values) - {f.name for f in fields(self.params_cls)}
        if unknown:
            raise ValueError(f"Variables desconocidas en {path.name}/argumentos: {sorted(unknown)}")
        self.p = self.params_cls(**values)

    def buy_signal(self, df: pd.DataFrame) -> pd.Series:
        """Serie booleana: condición de compra evaluada al CIERRE de cada día."""
        raise NotImplementedError

    def sell_signal(self, df: pd.DataFrame) -> pd.Series:
        """Serie booleana: venta a la apertura del día siguiente. Por defecto, nunca."""
        return pd.Series(False, index=df.index)


@dataclass
class Result:
    trades: pd.DataFrame
    equity: pd.Series
    metrics: dict = field(default_factory=dict)

    def summary(self) -> str:
        return "\n".join(f"{k:>18}: {v}" for k, v in self.metrics.items())


def _metrics(equity: pd.Series, trades: pd.DataFrame, in_pos: np.ndarray,
             close: pd.Series, p: Params) -> dict:
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    total = equity.iloc[-1] / p.initial_capital - 1
    daily = equity.pct_change().dropna()
    dd = (equity / equity.cummax() - 1).min()
    n = len(trades)
    return {
        "retorno_total_%": round(total * 100, 2),
        "CAGR_%": round(((1 + total) ** (1 / years) - 1) * 100, 2),
        "buy&hold_%": round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2),
        "max_drawdown_%": round(dd * 100, 2),
        "sharpe": round(daily.mean() / daily.std() * np.sqrt(252), 2) if daily.std() > 0 else None,
        "operaciones": n,
        "aciertos_%": round((trades["return_pct"] > 0).mean() * 100, 1) if n else None,
        "retorno_medio_op_%": round(trades["return_pct"].mean() * 100, 2) if n else None,
        "dias_medios_op": round(trades["days_held"].mean(), 1) if n else None,
        "exposicion_%": round(in_pos.mean() * 100, 1),
    }


def backtest(algo: Algorithm, df: pd.DataFrame) -> Result:
    """Ejecuta `algo` sobre `df` (precios + indicadores de UN símbolo, ordenado por fecha)."""
    p = algo.p
    missing = [c for c in OHLC + list(algo.requires) if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en los datos: {missing}")
    df = df.sort_values("date").reset_index(drop=True)

    # Señales al cierre de t -> se ejecutan en la apertura de t+1 (sin lookahead)
    buy = algo.buy_signal(df).shift(1, fill_value=False).fillna(False).to_numpy(bool)
    sell = algo.sell_signal(df).shift(1, fill_value=False).fillna(False).to_numpy(bool)

    o, h, c = (df[k].to_numpy(float) for k in ("open", "high", "close"))
    dates = df["date"].to_numpy()
    comm, slip = p.commission_pct, p.slippage_pct

    cash, shares, entry_i, entry_px, target = p.initial_capital, 0, -1, 0.0, np.inf
    trades, equity, in_pos = [], np.empty(len(df)), np.zeros(len(df), bool)

    def close_trade(i, px, reason):
        nonlocal cash, shares
        cash += shares * px * (1 - comm)
        trades.append({
            "entry_date": dates[entry_i], "entry_price": entry_px,
            "exit_date": dates[i], "exit_price": px, "shares": shares, "reason": reason,
            "return_pct": px / entry_px - 1, "days_held": i - entry_i,
            "pnl": shares * (px * (1 - comm) - entry_px * (1 + comm)),
        })
        shares = 0

    for i in range(len(df)):
        sold_today = False
        if shares:
            if sell[i]:
                close_trade(i, o[i] * (1 - slip), "senal_apertura"); sold_today = True
            elif p.max_hold_days is not None and i - entry_i >= p.max_hold_days:
                close_trade(i, o[i] * (1 - slip), "max_dias"); sold_today = True
            elif o[i] >= target:
                close_trade(i, o[i], "meta_gap"); sold_today = True
            elif h[i] >= target:
                close_trade(i, target, "meta"); sold_today = True

        if not shares and not sold_today and buy[i]:
            px = o[i] * (1 + slip)
            n = int(cash * p.position_fraction // (px * (1 + comm)))
            if n > 0:
                cash -= n * px * (1 + comm)
                shares, entry_i, entry_px = n, i, px
                target = px * (1 + p.target_pct) if p.target_pct is not None else np.inf
                if h[i] >= target:           # la meta se alcanza el mismo día de la compra
                    close_trade(i, target, "meta")

        in_pos[i] = shares > 0
        equity[i] = cash + shares * c[i]

    if shares:  # posición abierta al final: se valora al último cierre
        close_trade(len(df) - 1, c[-1], "fin_datos")
        equity[-1] = cash

    trades_df = pd.DataFrame(trades)
    eq = pd.Series(equity, index=pd.to_datetime(df["date"]), name="equity")
    return Result(trades_df, eq, _metrics(eq, trades_df, in_pos, df["close"], p))
