import random

import numpy as np
import pandas as pd

from algorithms.engine import Algorithm, backtest
from algorithms.genetic import GAConfig
from algorithms.portfolio import PortfolioConfig, backtest_portfolio, sample_portfolio_test


class _Signals(Algorithm):
    """Compra en las barras `buy_at` (por símbolo no importa: misma señal en todas las acciones)."""
    def __init__(self, buy_at, **kw):
        super().__init__(**kw)
        self._b = set(buy_at)

    def buy_signal(self, df):
        return pd.Series([i in self._b for i in range(len(df))], index=df.index)


def _frame(n=300, seed=0, irx=None, drift=0.0004):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
    o = c * (1 + rng.normal(0, 0.003, n))
    df = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=n), "open": o,
                       "high": np.maximum(o, c) * 1.004, "low": np.minimum(o, c) * 0.996, "close": c})
    if irx is not None:
        df["mkt_irx"] = irx
    return df


def test_one_stock_portfolio_equals_single_engine():
    df = _frame(seed=3)
    kw = dict(target_pct=0.03, stop_pct=0.04, max_hold_days=8)
    algo = _Signals(range(0, 300, 11), **kw)
    single = backtest(algo, df)
    port = backtest_portfolio(algo, {"A": df}, start_bar=0, max_positions=1, initial_capital=10_000)
    assert np.isclose(port.equity.iloc[-1], single.equity.iloc[-1])
    assert len(port.trades) == len(single.trades) and list(port.trades["reason"]) == list(single.trades["reason"])


def test_position_slots_and_capital_sharing():
    frames = {s: _frame(seed=i) for i, s in enumerate("ABC")}
    algo = _Signals([5], target_pct=None, commission_pct=0, slippage_pct=0, cash_interest=False)
    r = backtest_portfolio(algo, frames, start_bar=1, max_positions=2, initial_capital=100_000)
    opened = r.trades[r.trades["entry_date"] == frames["A"]["date"].iloc[6]]
    assert len(opened) == 2                                              # 3 señales, solo 2 posiciones
    assert (opened["shares"] * opened["entry_price"]).max() <= 50_000 + 1   # 1/max_positions del capital


def test_cash_only_portfolio_earns_risk_free_and_zero_alpha():
    frames = {s: _frame(seed=i, irx=4.0) for i, s in enumerate("AB")}
    r = backtest_portfolio(_Signals([]), frames, start_bar=0, max_positions=2)
    assert r.metrics["exposicion_%"] == 0 and r.metrics["CAGR_%"] > 3.5
    assert abs(r.metrics["alpha_timing_%"]) < 0.1


def test_sampler_period_and_stocks_have_data():
    cal = pd.bdate_range("2000-01-03", periods=3000)
    spans = pd.DataFrame({"first": [cal[0]] * 15 + [cal[1500]] * 25, "last": [cal[-1]] * 40},
                         index=[f"S{i}" for i in range(40)])
    load = lambda s: pd.DataFrame({"date": cal[spans.loc[s, "first"] == cal[0] and 0 or 1500:], "open": 1.0,
                                   "high": 1.0, "low": 1.0, "close": 1.0})
    cfg, pc = GAConfig(), PortfolioConfig()
    starts = set()
    for k in range(30):
        syms, frames, sb = sample_portfolio_test(spans, cal, load, cfg, pc, random.Random(k))
        assert len(set(syms)) == pc.n_stocks and sb >= pc.lead_bars
        lens = {len(f) for f in frames.values()}
        assert len(lens) == 1 and cfg.min_bars <= lens.pop() - sb <= cfg.max_bars
        assert all(f["date"].is_monotonic_increasing for f in frames.values())
        starts.add(frames[syms[0]]["date"].iloc[sb])
    assert len(starts) > 15                                              # fechas de inicio distintas


def test_sampler_respects_date_range():
    cal = pd.bdate_range("2000-01-03", periods=3000)
    spans = pd.DataFrame({"first": [cal[0]] * 40, "last": [cal[-1]] * 40}, index=[f"S{i}" for i in range(40)])
    load = lambda s: pd.DataFrame({"date": cal, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0})
    cfg, pc = GAConfig(), PortfolioConfig()
    lo, hi = pd.Timestamp("2004-01-01"), pd.Timestamp("2008-12-31")
    for k in range(25):
        syms, frames, sb = sample_portfolio_test(spans, cal, load, cfg, pc, random.Random(k), date_min=lo, date_max=hi)
        d = frames[syms[0]]["date"]
        assert d.iloc[sb] >= lo and d.iloc[-1] <= hi          # lo operado dentro del rango


def test_walkforward_trust_region_and_determinism():
    import optuna
    from algorithms.genetic import Gene
    from algorithms.walkforward import _bounds, _genome_from, _suggest, _enqueue_params, perturb
    fl = Gene("x", "float", 0.0, 10.0)
    it = Gene("n", "int", 3, 40)
    assert _bounds(fl, 4.0, 0.3) == (2.8, 5.2) and _bounds(fl, 9.0, 0.3)[1] == 10.0    # recorta al rango
    assert _bounds(fl, 4.0, None) == (0.0, 10.0)
    lo, hi = _bounds(it, 10, 0.1)
    assert lo == 9.0 and hi == 11.0                                                   # al menos ±1 en enteros
    genes = [fl, it, Gene("b", "bool"), Gene("o", "float", 0.0, 1.0, allow_none=True)]
    current = {"x": 4.0, "n": 10, "b": True, "o": None}
    study = optuna.create_study(sampler=optuna.samplers.TPESampler(seed=1))
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study.enqueue_trial(_enqueue_params(genes, current, 0.3))
    study.optimize(lambda t: sum(v for v in _suggest(t, genes, current, 0.3).values() if isinstance(v, float)), n_trials=15)
    for t in study.trials:
        g = _genome_from(t.params, genes, current)
        assert 2.8 <= g["x"] <= 5.2 and 7 <= g["n"] <= 13 and g["b"] is True and g["o"] is None
    p = perturb({"x": 4.0, "n": 10, "b": True, "o": None}, genes, random.Random(0), 0.1)
    assert 3.6 <= p["x"] <= 4.4 and p["n"] != 10 and p["o"] is None
