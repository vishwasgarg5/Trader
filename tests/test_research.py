import numpy as np
import pandas as pd
import pytest

from trader.research import add_relative_strength_features, merge_delivery_percentages


def test_relative_strength_uses_market_adjusted_returns_and_daily_rank():
    dates = pd.to_datetime(["2026-01-01", "2026-01-01"])
    frame = pd.DataFrame({
        "symbol": ["AAA.NS", "BBB.NS"],
        "ret_1": [0.01, 0.02],
        "ret_5": [0.05, 0.02],
        "ret_10": [0.08, 0.04],
        "ret_20": [0.10, 0.03],
        "nifty_ret_1": [0.005, 0.005],
        "nifty_ret_5": [0.01, 0.01],
        "nifty_ret_10": [0.02, 0.02],
        "nifty_ret_20": [0.03, 0.03],
    }, index=dates)
    result = add_relative_strength_features(frame)
    assert result.iloc[0]["relative_ret_5"] == pytest.approx(0.04)
    assert result.iloc[0]["relative_strength_rank_5"] == 1.0
    assert result.iloc[1]["relative_strength_rank_5"] == 0.5


def test_delivery_csv_is_optional_and_validated(tmp_path):
    index = pd.to_datetime(["2026-01-01"])
    frame = pd.DataFrame({"symbol": ["AAA.NS"]}, index=index)
    missing = merge_delivery_percentages(frame, tmp_path / "missing.csv")
    assert np.isnan(missing.iloc[0]["delivery_pct"])

    path = tmp_path / "delivery.csv"
    pd.DataFrame({
        "date": ["2026-01-01"],
        "symbol": ["AAA.NS"],
        "delivery_pct": [62.5],
    }).to_csv(path, index=False)
    merged = merge_delivery_percentages(frame, path)
    assert merged.iloc[0]["delivery_pct"] == pytest.approx(62.5)


def test_delivery_csv_rejects_duplicate_symbol_dates(tmp_path):
    path = tmp_path / "delivery.csv"
    pd.DataFrame({
        "date": ["2026-01-01", "2026-01-01"],
        "symbol": ["AAA.NS", "AAA.NS"],
        "delivery_pct": [60, 61],
    }).to_csv(path, index=False)
    frame = pd.DataFrame({"symbol": ["AAA.NS"]}, index=pd.to_datetime(["2026-01-01"]))
    with pytest.raises(ValueError, match="duplicate"):
        merge_delivery_percentages(frame, path)
