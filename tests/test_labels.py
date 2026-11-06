import numpy as np
import pandas as pd
import pytest

from trader.labels import triple_barrier_labels


def _bars(rows):
    index = pd.bdate_range("2026-01-01", periods=len(rows))
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    frame["atr"] = 2.0
    frame.index = index
    return frame


def test_target_barrier_is_labelled_positive_after_next_open_entry():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 105, 99, 104),
        (104, 105, 103, 104),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["entry_price"] == 100
    assert result.iloc[0]["target"] == 1
    assert result.iloc[0]["exit_reason"] == "target"


def test_stop_gap_uses_open_execution_price_after_entry_session():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 102, 99, 101),
        (90, 95, 88, 92),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["target"] == 0
    assert result.iloc[0]["exit_reason"] == "stop_gap"
    assert result.iloc[0]["exit_price"] == 90


def test_same_day_double_touch_is_ambiguous():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 105, 96, 101),
        (101, 102, 100, 101),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert np.isnan(result.iloc[0]["target"])
    assert result.iloc[0]["exit_reason"] == "ambiguous"


def test_timeout_uses_horizon_close_and_return_sign_from_next_open():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 101, 99, 100),
        (100, 102, 99, 101),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["target"] == 1
    assert result.iloc[0]["exit_reason"] == "timeout"
    assert result.iloc[0]["entry_price"] == 100
    assert result.iloc[0]["exit_price"] == 101


def test_last_horizon_rows_remain_unresolved():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 101, 99, 100),
        (100, 101, 99, 100),
    ])
    result = triple_barrier_labels(prices, horizon=2)
    assert result.iloc[0]["exit_reason"] == "timeout"
    assert result.iloc[0]["target"] == 0
    assert result.iloc[1:]["target"].isna().all()


def test_rejects_duplicate_trading_dates():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 105, 99, 104),
        (104, 105, 103, 104),
    ])
    prices.index = pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-03"])
    with pytest.raises(ValueError, match="unique trading dates"):
        triple_barrier_labels(prices, horizon=2)


@pytest.mark.parametrize("multiple", [float("nan"), float("inf"), 0.0, -1.0])
def test_rejects_non_finite_or_non_positive_barrier_multiples(multiple):
    prices = _bars([
        (100, 101, 99, 100),
        (100, 105, 99, 104),
        (104, 105, 103, 104),
    ])
    with pytest.raises(ValueError, match="finite and positive"):
        triple_barrier_labels(prices, horizon=2, up_multiple=multiple)


def test_rejects_inconsistent_ohlc_range():
    prices = _bars([
        (100, 101, 99, 100),
        (100, 99, 98, 100),
        (104, 105, 103, 104),
    ])
    with pytest.raises(ValueError, match="inconsistent high/low"):
        triple_barrier_labels(prices, horizon=2)


def test_rejects_non_finite_ohlc_values():
    prices = _bars([
        (100, 101, 99, 100),
        (100, np.inf, 99, 100),
        (104, 105, 103, 104),
    ])
    with pytest.raises(ValueError, match="finite and positive"):
        triple_barrier_labels(prices, horizon=2)
