import pandas as pd

from algorithms.engine import Algorithm, Params, backtest


class _Always(Algorithm):
    def __init__(self, buy_at, sell_at=(), **kw):
        super().__init__(**kw)
        self._b, self._s = buy_at, sell_at

    def buy_signal(self, df):
        return pd.Series([i in self._b for i in range(len(df))], index=df.index)

    def sell_signal(self, df):
        return pd.Series([i in self._s for i in range(len(df))], index=df.index)


def _df(opens, highs, closes):
    n = len(opens)
    return pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=n), "open": opens,
                         "high": highs, "low": opens, "close": closes})


def _p(**kw):
    return dict(commission_pct=0, slippage_pct=0, **kw)


def test_buy_next_open_and_target_intraday():
    # señal el día 0 -> compra en la apertura del día 1 (100); meta 5% = 105, high del día 2 = 106
    df = _df([100, 100, 101, 101], [100, 101, 106, 101], [100, 100, 103, 101])
    r = backtest(_Always([0], **_p(target_pct=0.05)), df)
    t = r.trades.iloc[0]
    assert t.entry_price == 100 and t.exit_price == 105 and t.reason == "meta"


def test_target_gap_fills_at_open():
    df = _df([100, 100, 110, 110], [100, 100, 111, 110], [100, 100, 110, 110])
    t = backtest(_Always([0], **_p(target_pct=0.05)), df).trades.iloc[0]
    assert t.exit_price == 110 and t.reason == "meta_gap"


def test_sell_signal_executes_next_open_and_max_hold():
    df = _df([100, 100, 100, 90, 95], [100, 100, 100, 90, 95], [100, 100, 100, 90, 95])
    t = backtest(_Always([0], [2], **_p(target_pct=None)), df).trades.iloc[0]
    assert t.exit_price == 90 and t.reason == "senal_apertura"
    t = backtest(_Always([0], **_p(target_pct=None, max_hold_days=2)), df).trades.iloc[0]
    assert t.reason == "max_dias" and t.days_held == 2


def test_stop_sells_next_open_after_close_below_stop():
    # compra open día1=100, stop 5% -> 95. close día2=94 => venta en la apertura del día3 (92)
    df = _df([100, 100, 100, 92, 92], [100, 100, 100, 92, 92], [100, 100, 94, 92, 92])
    t = backtest(_Always([0], **_p(target_pct=None, stop_pct=0.05)), df).trades.iloc[0]
    assert t.reason == "stop_apertura" and t.exit_price == 92 and t.exit_date == df["date"][3]


class _AtrTarget(_Always):
    target_atr_mult = 1.0

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.p.target_atr_mult = 1.0


def test_atr_target_uses_yesterdays_atr():
    df = _df([100, 100, 100, 100], [100, 100, 110, 100], [100, 100, 100, 100])
    df["atr_14"] = [5.0, 5.0, 5.0, 5.0]   # ATR% = 5% sobre close=100 -> meta +5% = 105
    t = backtest(_AtrTarget([0], **_p(target_pct=0.5)), df).trades.iloc[0]
    assert t.reason == "meta" and abs(t.exit_price - 105) < 1e-9
