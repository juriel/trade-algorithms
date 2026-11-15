import numpy as np
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


def test_features_ibs_and_rsi2():
    from algorithms import features as F
    df = pd.DataFrame({"open": [1, 1, 1, 1.], "high": [2, 2, 2, 1.], "low": [0, 0, 0, 1.], "close": [0, 1, 2, 1.]})
    ibs = F.ibs(df)
    assert list(ibs[:3]) == [0.0, 0.5, 1.0] and np.isnan(ibs[3])   # rango 0 -> NaN, no divide por cero
    r = F.rsi(pd.DataFrame({"close": np.arange(1, 30, dtype=float)}), 2)
    assert r.iloc[-1] > 99 and r.index.equals(pd.RangeIndex(29))


def test_calendar_volume_and_relative_strength_features():
    from algorithms import features as F
    d = pd.DataFrame({"date": pd.to_datetime(["2024-01-29", "2024-01-30", "2024-01-31", "2024-03-28", "2024-03-29"])})
    assert list(F.business_days_left(d)) == [2, 1, 0, 1, 0]          # 31-ene-2024 miércoles; 29-mar viernes
    v = pd.DataFrame({"volume": [10.0] * 20 + [50.0]})
    assert F.volume_ratio(v).iloc[-1] == 5.0 and np.isnan(F.volume_ratio(v).iloc[0])   # solo compara con días anteriores
    s = pd.DataFrame({"close": np.linspace(100, 200, 130), "mkt_spx_ret120": 30.0})
    assert abs(F.rel_strength(s, 120).iloc[-1] - ((200 / s["close"].iloc[9] - 1) * 100 - 30.0)) < 1e-9
