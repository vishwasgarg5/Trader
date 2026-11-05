import numpy as np
import pandas as pd

from trader.labels import triple_barrier_labels


def _bars(rows):
    index = pd.bdate_range("2026-01-01", periods=len(rows))
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    frame["atr"] = 2.0
    frame.index = index
    return frame


def test_target_barrier_is_labelled_positive():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 105, 99, 104),
        (104, 105, 103, 104),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["target"] == 1
    assert result.iloc[0]["exit_reason"] == "target"


def test_stop_gap_uses_open_execution_price():
    prices = _bars([
        (100, 101, 99, 100),
        (96, 98, 95, 97),
        (97, 99, 96, 98),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["target"] == 0
    assert result.iloc[0]["exit_reason"] == "stop_gap"
    assert result.iloc[0]["exit_price"] == 96


def test_same_day_double_touch_is_ambiguous():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 105, 96, 101),
        (101, 102, 100, 101),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert np.isnan(result.iloc[0]["target"])
    assert result.iloc[0]["exit_reason"] == "ambiguous"


def test_timeout_uses_horizon_close_and_return_sign():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 101, 99, 100),
        (100, 102, 99, 101),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["target"] == 1
    assert result.iloc[0]["exit_reason"] == "timeout"
    assert result.iloc[0]["exit_price"] == 101


def test_last_horizon_rows_remain_unresolved():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 101, 99, 100),
        (100, 101, 99, 100),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["exit_reason"] == "timeout"\n    assert result.iloc[0]["target"] == 0\n    assert result.iloc[1:]["target"].isna().all()
