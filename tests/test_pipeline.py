"""Pruebas offline con datos sintéticos (sin red)."""
import numpy as np
import pandas as pd

from ticker2db import StockDB, add_indicators


def _fake(symbol, n=300):
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({
        "symbol": symbol, "date": pd.bdate_range("2023-01-02", periods=n),
        "open": close, "high": close + 1, "low": close - 1, "close": close,
        "adj_close": close, "volume": rng.integers(1e5, 1e6, n).astype(float),
    })


def test_roundtrip(tmp_path):
    df = pd.concat([_fake("AAA"), _fake("BBB")], ignore_index=True)
    full = add_indicators(df)
    assert {"sma_20", "rsi_14", "macd_hist", "bb_upper", "stoch_k"} <= set(full.columns)
    ind = [c for c in full.columns if c not in df.columns]
    with StockDB(str(tmp_path / "t.db")) as db:
        db.save_prices(df)
        db.save_indicators(full[["symbol", "date"] + ind])
        db.save_indicators(full[["symbol", "date"] + ind])  # upsert idempotente
        out = db.load(["AAA", "BBB"])
        assert len(out) == len(df)
        assert out["rsi_14"].notna().sum() > 0
        assert db.last_date("AAA") == df["date"].max()


def test_parse_sp500_html():
    from ticker2db.universe import parse_sp500_html
    html = """<table><tr><th>#</th><th>Company</th><th>Symbol</th><th>Weight</th><th>Price</th></tr>
    <tr><td>1</td><td>Apple Inc.</td><td>AAPL</td><td>7.12%</td><td>200</td></tr>
    <tr><td>2</td><td>Berkshire Hathaway</td><td>BRK.B</td><td>1.60%</td><td>450</td></tr></table>"""
    df = parse_sp500_html(html)
    assert df["weight"].tolist() == [7.12, 1.60]
    assert df["yf_symbol"].tolist() == ["AAPL", "BRK-B"]
