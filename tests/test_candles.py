import numpy as np
import pandas as pd
import pytest

from ticker2db import StockDB, add_candle_patterns, candle_summary, pattern_info, update_candles
from ticker2db.candles import COMMON_PATTERNS, pattern_functions


def _random(n=120, seed=0, symbol="AAA"):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    o = c + rng.normal(0, 0.5, n)
    return pd.DataFrame({"symbol": symbol, "date": pd.bdate_range("2023-01-02", periods=n), "open": o,
                         "high": np.maximum(o, c) + rng.random(n), "low": np.minimum(o, c) - rng.random(n),
                         "close": c, "adj_close": c, "volume": 1e6})


def test_all_patterns_present_and_valid():
    out = add_candle_patterns(_random())
    cdl = [c for c in out.columns if c.startswith("cdl_")]
    assert len(cdl) == len(pattern_functions()) == 61 and set(cdl) >= {"cdl_engulfing", "cdl_hammer", "cdl_3whitesoldiers"}
    assert set(np.unique(out[cdl].to_numpy())) <= {-200, -100, 0, 100, 200}
    assert out[cdl].abs().to_numpy().sum() > 0                       # con datos aleatorios hay patrones
    assert set(COMMON_PATTERNS) <= set(pattern_info())


def test_bullish_engulfing_detected():
    df = _random(40)
    n = len(df)
    # vela bajista (10 -> 9) seguida de una alcista que la envuelve (8.5 -> 10.5)
    df.loc[n - 2, ["open", "high", "low", "close"]] = [10, 10.2, 8.9, 9]
    df.loc[n - 1, ["open", "high", "low", "close"]] = [8.5, 10.6, 8.4, 10.5]
    out = add_candle_patterns(df, ["ENGULFING"])
    assert out["cdl_engulfing"].iloc[-1] == 100 and list(out.filter(like="cdl_").columns) == ["cdl_engulfing"]


def test_no_lookahead_prefix_equals_full():
    df = _random(200)
    full = add_candle_patterns(df, COMMON_PATTERNS)
    part = add_candle_patterns(df.iloc[:150], COMMON_PATTERNS)
    cols = [c for c in full.columns if c.startswith("cdl_")]
    assert (full[cols].iloc[:150].to_numpy() == part[cols].to_numpy()).all()


def test_unknown_pattern_and_summary():
    with pytest.raises(ValueError):
        add_candle_patterns(_random(), ["NOEXISTE"])
    out = add_candle_patterns(_random(), COMMON_PATTERNS)
    s = candle_summary(out)
    assert (s["cdl_net"] == s["cdl_bull_count"] - s["cdl_bear_count"]).all() and len(s) == len(out)


def test_storage_roundtrip(tmp_path):
    path = str(tmp_path / "t.db")
    with StockDB(path) as db:
        db.save_prices(_random(symbol="AAA"))
        db.save_prices(_random(seed=1, symbol="BBB"))
        assert not db.has_candles()
    assert update_candles(path, patterns=COMMON_PATTERNS) == 240
    assert update_candles(path, patterns=COMMON_PATTERNS) == 240      # idempotente
    with StockDB(path) as db:
        assert db.has_candles()
        out = db.load("AAA", with_indicators=False, with_candles=True)
        assert len(out) == 120 and f"cdl_{'engulfing'}" in out.columns
        ref = add_candle_patterns(_random(symbol="AAA"), COMMON_PATTERNS)
        assert (out["cdl_engulfing"].to_numpy() == ref["cdl_engulfing"].to_numpy()).all()
        assert not any(c.startswith("cdl_") for c in db.load("AAA", with_indicators=False).columns)   # opt-in


def test_summary_excludes_neutral_patterns_by_default():
    from ticker2db import NEUTRAL_PATTERNS
    df = pd.DataFrame({"cdl_doji": [100, 0], "cdl_hammer": [0, 100], "cdl_engulfing": [-100, 0]})
    s = candle_summary(df)
    assert list(s["cdl_bull_count"]) == [0, 1] and list(s["cdl_bear_count"]) == [1, 0]
    assert list(candle_summary(df, include_neutral=True)["cdl_bull_count"]) == [1, 1]
    assert "CDLDOJI" in NEUTRAL_PATTERNS
