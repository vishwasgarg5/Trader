import numpy as np
import pandas as pd
import pytest

from trader.research import (
    add_relative_strength_features, merge_delivery_percentages, purge_training_rows,
    summarize_outcome_reasons,
)


def test_relative_strength_uses_market_adjusted_returns_and_daily_rank():
    dates = pd.to_datetime(["2026-01-01", "2026-01-01"])
    frame = pd.DataFrame({
        "symbol": ["AAA.NS", "BBB.NS"],
        "ret_1": [0.01, 0.02], "ret_5": [0.05, 0.02],
        "ret_10": [0.08, 0.04], "ret_20": [0.10, 0.03],
        "nifty_ret_1": [0.005, 0.005], "nifty_ret_5": [0.01, 0.01],
        "nifty_ret_10": [0.02, 0.02], "nifty_ret_20": [0.03, 0.03],
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
        "date": ["2026-01-01"], "symbol": ["AAA.NS"], "delivery_pct": [62.5],
    }).to_csv(path, index=False)
    merged = merge_delivery_percentages(frame, path)
    assert merged.iloc[0]["delivery_pct"] == pytest.approx(62.5)


def test_delivery_csv_rejects_duplicate_symbol_dates(tmp_path):
    path = tmp_path / "delivery.csv"
    pd.DataFrame({
        "date": ["2026-01-01", "2026-01-01"],
        "symbol": ["AAA.NS", "AAA.NS"], "delivery_pct": [60, 61],
    }).to_csv(path, index=False)
    frame = pd.DataFrame({"symbol": ["AAA.NS"]}, index=pd.to_datetime(["2026-01-01"]))
    with pytest.raises(ValueError, match="duplicate"):
        merge_delivery_percentages(frame, path)


def test_purge_uses_actual_label_exit_date_not_weekday_offset():
    dates = pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"])
    frame = pd.DataFrame({
        "target": [1, 0, 1],
        "exit_date": pd.to_datetime(["2026-01-12", "2026-01-09", "2026-01-08"]),
    }, index=dates)
    train, method = purge_training_rows(
        frame, pd.Timestamp("2026-01-12"), pd.Timestamp("2026-01-01"), 5
    )
    assert method == "actual_exit_date"
    assert list(train.index) == [pd.Timestamp("2026-01-06"), pd.Timestamp("2026-01-07")]


def test_outcome_summary_separates_barriers_and_timeouts_with_net_returns():
    frame = pd.DataFrame({
        "exit_reason": ["target", "stop", "timeout", "timeout"],
        "outcome_return": [0.04, -0.03, 0.002, -0.001],
        "net_return": [0.037, -0.033, -0.001, -0.004],
    })
    result = summarize_outcome_reasons(frame)
    assert result["target"]["rows"] == 1
    assert result["stop"]["gross_positive_fraction"] == 0.0
    assert result["timeout"]["rows"] == 2
    assert result["timeout"]["gross_positive_fraction"] == 0.5
    assert result["timeout"]["net_positive_fraction"] == 0.0
    assert result["timeout"]["mean_net_return"] == pytest.approx(-0.0025)
