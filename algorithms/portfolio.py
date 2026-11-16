"""Backtest de CARTERA: varias acciones a la vez con capital compartido.

Cada prueba = un periodo (fecha de inicio y largo al azar) + `n_stocks` acciones al azar que tengan datos en ese
periodo. Las reglas de cada algoritmo (compra a la apertura, venta a la apertura o al cumplir la meta, stops) son
las mismas del motor de una acción (`engine.py`); aquí se añaden:
  * capital compartido: hasta `max_positions` posiciones abiertas, cada una con 1/max_positions del capital actual
    (por `position_fraction`); el efectivo rinde la letra a 13 semanas;
  * si hay más señales de compra que posiciones libres, se eligen al azar (con semilla);
  * benchmark: las mismas acciones a partes iguales, comprar y mantener. Alpha de timing = CAGR de la cartera
    menos [exposición media × CAGR del benchmark + (1 − exposición) × tasa libre de riesgo].

Uso:  python -m algorithms.portfolio algorithm03a --tests 5 --seed 1 [--set max_positions=5]
"""
from __future__ import annotations

import argparse
import ast
import random
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .engine import Algorithm, OHLC, load_cfg
from .genetic import GAConfig, load_ga_config

HERE = Path(__file__).parent


@dataclass
class PortfolioConfig:
    n_stocks: int = 20
    min_eligible: int = 25
    lead_bars: int = 150
    max_positions: int = 10
    initial_capital: float = 100_000.0


def load_portfolio_config(path=HERE / "portfolio.cfg", **overrides) -> PortfolioConfig:
    values = load_cfg(path, "portfolio") if Path(path).exists() else {}
    values.update(overrides)
    return PortfolioConfig(**values)


@dataclass
class PortfolioResult:
    trades: pd.DataFrame
    equity: pd.Series
    metrics: dict


def _prepare(algo: Algorithm, df: pd.DataFrame) -> dict:
    """Señales y niveles de un símbolo, como en `engine.backtest` (señal al cierre de t -> ejecución en t+1)."""
    missing = [c for c in OHLC + list(algo.requires) if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en los datos: {missing}")
    sh = lambda s: s.shift(1, fill_value=False).fillna(False).to_numpy(bool)
    tp, sp = algo.target_series(df), algo.stop_series(df)
    return {"o": df["open"].to_numpy(float), "h": df["high"].to_numpy(float), "c": df["close"].to_numpy(float),
            "buy": sh(algo.buy_signal(df)), "sell": sh(algo.sell_signal(df)),
            "tp": None if tp is None else tp.shift(1).to_numpy(float),
            "sp": None if sp is None else sp.shift(1).to_numpy(float)}


def backtest_portfolio(algo: Algorithm, frames: Dict[str, pd.DataFrame], start_bar: int,
                       max_positions: int = 10, initial_capital: float = 100_000.0,
                       seed: int = 0) -> PortfolioResult:
    """`frames`: símbolo -> DataFrame alineado (mismas fechas, mismo largo). Se opera desde `start_bar`;
    las jornadas anteriores solo sirven para calcular indicadores y señales."""
    p = algo.p
    syms = list(frames)
    first = frames[syms[0]]
    T = len(first)
    dates = pd.to_datetime(first["date"]).to_numpy()
    arr = {s: _prepare(algo, frames[s]) for s in syms}
    comm, slip = p.commission_pct, p.slippage_pct
    rng = np.random.default_rng(seed)

    have_rf = p.cash_interest and "mkt_irx" in first.columns
    dt = np.r_[0.0, np.diff(dates.astype("datetime64[D]").astype(int))] / 365.0
    rf_growth = (np.exp((first["mkt_irx"].shift(1) / 100).fillna(0).to_numpy(float) * dt) if have_rf else np.ones(T))
    rf_annual = float((np.exp(first["mkt_irx"].iloc[start_bar:].mean() / 100) - 1) * 100) if have_rf else 0.0

    cash = initial_capital
    pos: Dict[str, dict] = {}
    trades: List[dict] = []
    n_out = T - start_bar
    equity, invested = np.empty(n_out), np.empty(n_out)

    def close_pos(s, i, px, reason):
        nonlocal cash
        q = pos.pop(s)
        cash += q["shares"] * px * (1 - comm)
        trades.append({"symbol": s, "entry_date": dates[q["i"]], "entry_price": q["px"], "exit_date": dates[i],
                       "exit_price": px, "shares": q["shares"], "reason": reason, "days_held": i - q["i"],
                       "return_pct": px / q["px"] - 1,
                       "pnl": q["shares"] * (px * (1 - comm) - q["px"] * (1 + comm))})

    for i in range(start_bar, T):
        cash *= rf_growth[i]
        sold_today = set()
        for s in list(pos):
            a, q = arr[s], pos[s]
            if a["sell"][i]:
                close_pos(s, i, a["o"][i] * (1 - slip), "senal_apertura")
            elif a["c"][i - 1] <= q["stop"]:
                close_pos(s, i, a["o"][i] * (1 - slip), "stop_apertura")
            elif p.max_hold_days is not None and i - q["i"] >= p.max_hold_days:
                close_pos(s, i, a["o"][i] * (1 - slip), "max_dias")
            elif a["o"][i] >= q["target"]:
                close_pos(s, i, a["o"][i], "meta_gap")
            elif a["h"][i] >= q["target"]:
                close_pos(s, i, q["target"], "meta")
            else:
                continue
            sold_today.add(s)

        cands = [s for s in syms if s not in pos and s not in sold_today and arr[s]["buy"][i]]
        slots = max_positions - len(pos)
        if cands and slots > 0:
            if len(cands) > slots:
                cands = [cands[j] for j in sorted(rng.choice(len(cands), slots, replace=False))]
            eq_open = cash + sum(q["shares"] * arr[s]["o"][i] for s, q in pos.items())
            for s in cands:
                a = arr[s]
                px = a["o"][i] * (1 + slip)
                budget = min(eq_open / max_positions * p.position_fraction, cash)
                n = int(budget // (px * (1 + comm)))
                if n <= 0:
                    continue
                cash -= n * px * (1 + comm)
                t_pct = a["tp"][i] if a["tp"] is not None and not np.isnan(a["tp"][i]) else p.target_pct
                s_pct = a["sp"][i] if a["sp"] is not None and not np.isnan(a["sp"][i]) else p.stop_pct
                pos[s] = {"shares": n, "i": i, "px": px,
                          "target": px * (1 + t_pct) if t_pct is not None else np.inf,
                          "stop": px * (1 - s_pct) if s_pct is not None else 0.0}
                if a["h"][i] >= pos[s]["target"]:       # la meta se alcanza el mismo día de la compra
                    close_pos(s, i, pos[s]["target"], "meta")

        inv = sum(q["shares"] * arr[s]["c"][i] for s, q in pos.items())
        equity[i - start_bar] = cash + inv
        invested[i - start_bar] = inv

    for s in list(pos):                                  # posiciones abiertas al final: se valoran al último cierre
        close_pos(s, T - 1, arr[s]["c"][-1], "fin_datos")
    equity[-1] = cash
    invested[-1] = 0.0 if not len(trades) else invested[-1]

    eq = pd.Series(equity, index=pd.to_datetime(dates[start_bar:]), name="equity")
    tr = pd.DataFrame(trades)
    # benchmark: mismas acciones a partes iguales, compradas a la apertura inicial y mantenidas
    bh = np.mean([arr[s]["c"][start_bar:] / arr[s]["o"][start_bar] for s in syms], axis=0)
    return PortfolioResult(tr, eq, _metrics(eq, tr, invested / equity, bh, initial_capital, rf_annual))


def _metrics(eq: pd.Series, tr: pd.DataFrame, expo: np.ndarray, bh: np.ndarray, capital: float, rf: float) -> dict:
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    total = eq.iloc[-1] / capital - 1
    cagr = ((1 + total) ** (1 / years) - 1) * 100
    bh_cagr = (bh[-1] ** (1 / years) - 1) * 100
    e = float(np.mean(expo))
    daily = eq.pct_change().dropna()
    return {
        "retorno_total_%": round(total * 100, 2), "CAGR_%": round(cagr, 2),
        "bh_CAGR_%": round(bh_cagr, 2), "rf_CAGR_%": round(rf, 2),
        "alpha_timing_%": round(cagr - (e * bh_cagr + (1 - e) * rf), 2),
        "max_drawdown_%": round((eq / eq.cummax() - 1).min() * 100, 2),
        "bh_max_drawdown_%": round((bh / np.maximum.accumulate(bh) - 1).min() * 100, 2),
        "sharpe": round(daily.mean() / daily.std() * np.sqrt(252), 2) if daily.std() > 0 else None,
        "operaciones": len(tr), "aciertos_%": round((tr["return_pct"] > 0).mean() * 100, 1) if len(tr) else None,
        "exposicion_%": round(e * 100, 1),
    }


# ----------------------------- sorteo de pruebas -----------------------------
Test = Tuple[List[str], Dict[str, pd.DataFrame], int]   # (símbolos, DataFrames alineados, start_bar)


def sample_portfolio_test(spans: pd.DataFrame, calendar: pd.DatetimeIndex, load: Callable[[str], pd.DataFrame],
                          cfg: GAConfig, pc: PortfolioConfig, rng: random.Random,
                          columns: Optional[List[str]] = None, date_min=None, date_max=None) -> Test:
    """Una prueba: periodo al azar (largo `min_bars`..`max_bars` jornadas, inicio al azar entre las fechas con al
    menos `min_eligible` acciones con historia) y `n_stocks` acciones al azar entre las que tienen datos en todo el periodo.

    `spans`: DataFrame indexado por símbolo con `first` y `last` (fechas). `calendar`: fechas de mercado.
    `date_min`/`date_max` (opcionales) obligan a que TODAS las jornadas operadas caigan en ese rango (las jornadas
    previas `lead_bars` solo calientan indicadores); sirven para separar entrenamiento y prueba en el tiempo."""
    N = len(calendar)
    lo_s = pc.lead_bars if date_min is None else max(pc.lead_bars, int(calendar.searchsorted(pd.Timestamp(date_min))))
    hi_e = N if date_max is None else int(calendar.searchsorted(pd.Timestamp(date_max), side="right"))   # fin exclusivo
    for _ in range(5000):
        L = rng.randint(cfg.min_bars, min(cfg.max_bars, hi_e - lo_s))
        if hi_e - lo_s < cfg.min_bars:
            raise RuntimeError("El rango de fechas es más corto que el largo mínimo de la prueba")
        s = rng.randint(lo_s, hi_e - L)
        d0, d1 = calendar[s - pc.lead_bars], calendar[s + L - 1]
        elig = spans.index[(spans["first"] <= d0) & (spans["last"] >= d1)].tolist()
        if len(elig) >= max(pc.min_eligible, pc.n_stocks):
            break
    else:
        raise RuntimeError("No se encontró un periodo con suficientes acciones")
    chosen = rng.sample(elig, pc.n_stocks)
    raw = {}
    for sym in chosen:
        df = load(sym)
        df = df[(df["date"] >= d0) & (df["date"] <= d1)]
        raw[sym] = df.set_index("date")
    common = None
    for df in raw.values():
        common = df.index if common is None else common.intersection(df.index)
    common = common.sort_values()
    frames = {}
    for sym, df in raw.items():
        f = df.loc[common].reset_index()
        frames[sym] = f[[c for c in f.columns if columns is None or c in columns or c in ("date",)]]
    start_bar = int(common.searchsorted(calendar[s]))
    return chosen, frames, start_bar


def main():
    from ticker2db import StockDB
    from .genetic import loader, make_algo
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("algorithm")
    ap.add_argument("--tests", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--set", nargs="*", default=[], metavar="clave=valor", help="sobrescribe portfolio.cfg")
    a = ap.parse_args()
    cfg = load_ga_config()
    pc = load_portfolio_config(**{k: ast.literal_eval(v) for k, v in (s.split("=", 1) for s in a.set)})
    algo = make_algo(a.algorithm)
    with StockDB(cfg.db_path) as db:
        load = loader(db, [a.algorithm])
        spans = pd.read_sql_query("SELECT symbol, MIN(date) AS first, MAX(date) AS last FROM prices WHERE interval='1d' "
                                  "GROUP BY symbol", db.conn, parse_dates=["first", "last"]).set_index("symbol")
        spans = spans.loc[db.symbols()]
        cal = pd.DatetimeIndex(db.load("^GSPC", with_indicators=False)["date"])
        for k in range(a.tests):
            syms, frames, sb = sample_portfolio_test(spans, cal, load, cfg, pc, random.Random(f"{a.seed}-{k}"))
            d = frames[syms[0]]["date"]
            m = backtest_portfolio(algo, frames, sb, pc.max_positions, pc.initial_capital, seed=k).metrics
            print(f"prueba {k + 1}: {d.iloc[sb].date()} → {d.iloc[-1].date()} ({len(d) - sb} jornadas), {len(syms)} acciones | "
                  f"CAGR {m['CAGR_%']}%  benchmark {m['bh_CAGR_%']}%  alpha {m['alpha_timing_%']}  DD {m['max_drawdown_%']}%  "
                  f"expo {m['exposicion_%']}%  ops {m['operaciones']}")


if __name__ == "__main__":
    main()
