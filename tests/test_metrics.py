import numpy as np
import pandas as pd

from algorithms.engine import Algorithm, Params, backtest
from algorithms.metrics import bh_adjust, bootstrap_ci, mean_pvalue, summarize_tests


class _Never(Algorithm):
    def buy_signal(self, df):
        return pd.Series(False, index=df.index)


class _BuyDay0(Algorithm):
    def buy_signal(self, df):
        return pd.Series([i == 0 for i in range(len(df))], index=df.index)


def _df(n=500, drift=0.0004, irx=5.0, seed=0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.01, n)))
    return pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=n), "open": c, "high": c * 1.002,
                         "low": c * 0.998, "close": c, "mkt_irx": irx})


def test_cash_earns_interest_and_alpha_of_staying_out_is_zero():
    r = backtest(_Never(**dict(target_pct=None)), _df())
    assert r.metrics["exposicion_%"] == 0 and r.metrics["CAGR_%"] > 4.5      # el efectivo rinde ~5%
    assert abs(r.metrics["alpha_timing_%"]) < 0.1                            # estar fuera no genera alpha


def test_no_interest_without_market_data_or_when_disabled():
    df = _df().drop(columns="mkt_irx")
    assert backtest(_Never(target_pct=None), df).metrics["CAGR_%"] == 0
    assert backtest(_Never(target_pct=None, cash_interest=False), _df()).metrics["CAGR_%"] == 0


def test_always_invested_has_alpha_near_zero_vs_its_own_stock():
    m = backtest(_BuyDay0(target_pct=None, commission_pct=0, slippage_pct=0), _df()).metrics
    assert m["exposicion_%"] > 99 and abs(m["alpha_timing_%"]) < 1.0         # comprar y mantener = benchmark de su exposición


def test_bootstrap_ci_pvalue_and_bh():
    x = np.random.default_rng(0).normal(1.0, 3.0, 400)
    lo, hi = bootstrap_ci(x, seed=1)
    assert lo < x.mean() < hi and lo > 0
    assert mean_pvalue(x) < 0.001 and mean_pvalue(-x) > 0.99
    adj = bh_adjust([0.001, 0.04, 0.5])
    assert (adj >= np.array([0.001, 0.04, 0.5])).all() and adj.max() <= 1 and adj[0] < adj[1] <= adj[2]


def test_summarize_tests_flags_significant_algorithm():
    rng = np.random.default_rng(2)
    t = pd.concat([pd.DataFrame({"algorithm": "bueno", "alpha": rng.normal(2, 3, 300)}),
                   pd.DataFrame({"algorithm": "ruido", "alpha": rng.normal(0, 3, 300)})])
    s = summarize_tests(t)
    assert bool(s.loc["bueno", "significativo"]) and not bool(s.loc["ruido", "significativo"])
    assert s.loc["bueno", "alpha_ic_inf"] > 0
