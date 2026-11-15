import numpy as np
import pandas as pd

from ticker2db import StockDB, market_symbols
from ticker2db.market import MARKET_SYMBOLS, market_features


def _px(symbol, n=400, seed=0, volume=1e6, start="2022-01-03"):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"symbol": symbol, "date": pd.bdate_range(start, periods=n), "open": c, "high": c + 1,
                         "low": c - 1, "close": c, "adj_close": c, "volume": volume})


def _db(tmp_path):
    db = StockDB(str(tmp_path / "t.db"))
    for i, s in enumerate(["AAA", "BBB"]):
        db.save_prices(_px(s, seed=i))
    for i, s in enumerate(["^VIX", "^GSPC"]):
        db.save_prices(_px(s, seed=10 + i, volume=0))
    db.register_symbols([("^VIX", "volatilidad", "VIX"), ("^GSPC", "indices", "S&P 500")])
    return db


def test_market_symbols_catalog():
    names = [s for s, _, _ in market_symbols()]
    assert {"^VIX", "DX-Y.NYB", "^GSPC", "SPY", "QQQ", "TLT", "GLD", "XLK"} <= set(names)
    assert len(names) == len(set(names))
    assert [s for s, _, _ in market_symbols(["volatilidad"])] == list(MARKET_SYMBOLS["volatilidad"])


def test_market_symbols_excluded_from_stock_universe(tmp_path):
    with _db(tmp_path) as db:
        assert db.symbols() == ["AAA", "BBB"]
        assert set(db.symbols(include_market=True)) == {"AAA", "BBB", "^VIX", "^GSPC"}
        assert db.market_symbols() == ["^GSPC", "^VIX"] and db.has_market()


def test_features_partial_data_and_no_lookahead(tmp_path):
    with _db(tmp_path) as db:
        mf = market_features(db, breadth=False)
        assert {"mkt_vix", "mkt_vix_ratio50", "mkt_spx_above_sma200", "mkt_spx_dd252"} <= set(mf.columns)
        assert "mkt_dxy" not in mf.columns            # sin DXY en la BD simplemente no hay columna
        # la variable de un día solo depende de datos hasta ese día
        vix = db.load("^VIX", with_indicators=False).set_index("date")["close"]
        trunc = pd.DataFrame({"symbol": "^VIX", "date": vix.index[:300], "open": vix[:300], "high": vix[:300],
                              "low": vix[:300], "close": vix[:300], "adj_close": vix[:300], "volume": 0.0})
    with StockDB(str(tmp_path / "t2.db")) as db2:
        db2.save_prices(trunc)
        db2.register_symbols([("^VIX", "volatilidad", "VIX")])
        short = market_features(db2, breadth=False)
    both = mf["mkt_vix_ratio50"].iloc[:300].dropna()
    assert np.allclose(both, short["mkt_vix_ratio50"].reindex(both.index).dropna(), equal_nan=True)


def test_load_with_market_merges_by_date(tmp_path):
    with _db(tmp_path) as db:
        out = db.load("AAA", with_indicators=False, with_market=True)
        assert len(out) == 400 and "mkt_vix" in out.columns
        vix = db.load("^VIX", with_indicators=False).set_index("date")["close"]
        assert np.isclose(out["mkt_vix"].iloc[10], vix.iloc[10])
        assert "mkt_vix" not in db.load("AAA", with_indicators=False).columns   # opt-in


def test_total_returns_ranks_and_filters_short_history():
    from ticker2db.universe import total_returns
    idx = pd.bdate_range("2021-01-01", periods=300)
    prices = pd.DataFrame({"UP": np.linspace(100, 200, 300), "DOWN": np.linspace(100, 40, 300),
                           "SHORT": [np.nan] * 250 + list(np.linspace(10, 20, 50))}, index=idx)
    r = total_returns(prices, min_obs=200)
    assert list(r.sort_values().index) == ["DOWN", "UP"] and abs(r["DOWN"] + 0.6) < 1e-9   # SHORT se descarta
