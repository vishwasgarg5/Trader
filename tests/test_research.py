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


def test_cross_sectional_frame_ranks_features_and_labels_against_daily_median():
    from trader.research import make_cross_sectional_frame

    dates = pd.to_datetime(["2026-01-01"] * 3 + ["2026-01-02"] * 3)
    frame = pd.DataFrame({
        "symbol": ["A", "B", "C", "A", "B", "C"],
        "ret_5": [0.03, 0.01, 0.02, 0.01, 0.03, 0.02],
        "nifty_ret_5": [0.01] * 6,
        "net_return": [0.04, -0.01, 0.01, -0.02, 0.03, 0.01],
    }, index=dates)
    ranked, features = make_cross_sectional_frame(frame, ["ret_5", "nifty_ret_5"])
    assert features == ["ret_5"]
    assert ranked.iloc[0]["ret_5"] == pytest.approx(1.0)
    assert ranked.iloc[1]["ret_5"] == pytest.approx(1 / 3)
    assert list(ranked["target"].astype(int)) == [1, 0, 0, 0, 1, 0]


def test_block_bootstrap_is_reproducible_and_returns_interval():
    from trader.research import block_bootstrap_mean_ci

    values = np.linspace(-0.002, 0.003, 40)
    first = block_bootstrap_mean_ci(values, repeats=300)
    second = block_bootstrap_mean_ci(values, repeats=300)
    assert first == second
    assert first["method"] == "circular_moving_block_bootstrap"
    assert first["lower"] <= float(values.mean()) <= first["upper"]


def test_regime_summary_compares_top_five_with_universe_by_predeclared_bins():
    from trader.research import summarize_regime_performance

    dates = pd.to_datetime(["2026-01-01"] * 6 + ["2026-01-02"] * 6)
    test = pd.DataFrame({
        "symbol": list("ABCDEF") * 2,
        "net_return": [0.01, 0.02, -0.01, 0.0, 0.01, 0.0] * 2,
        "nifty_above_200dma": [True] * 6 + [False] * 6,
        "india_vix_low_20": [True] * 12,
    }, index=dates)
    daily_top = test.groupby(level=0).head(2)
    result = summarize_regime_performance(test, daily_top)
    assert result["nifty_above_200dma_vix_below_20"]["days"] == 1
    assert result["nifty_at_or_below_200dma_vix_below_20"]["days"] == 1
    assert result["nifty_above_200dma_vix_below_20"]["top5_mean_net_return"] == pytest.approx(0.015)


def test_simple_factor_baselines_use_fixed_rank_rules_and_net_returns():
    from trader.research import evaluate_simple_factor_baselines

    dates = pd.bdate_range("2020-01-01", periods=520)
    rows = []
    for date in dates:
        for symbol, ret5, atr, rel20, net in [
            ("A", 0.1, 0.9, 0.1, -0.01),
            ("B", 0.2, 0.8, 0.2, -0.02),
            ("C", 0.3, 0.7, 0.3, 0.01),
            ("D", 0.4, 0.6, 0.4, 0.02),
            ("E", 0.5, 0.5, 0.5, 0.03),
            ("F", 0.6, 0.4, 0.6, 0.04),
        ]:
            rows.append({
                "date": date, "symbol": symbol, "ret_5": ret5,
                "atr_pct": atr, "relative_ret_20": rel20, "net_return": net,
            })
    frame = pd.DataFrame(rows).set_index("date")
    result = evaluate_simple_factor_baselines(
        frame, train_years=1, test_months=3, picks_per_day=5,
    )
    factors = result["factor_results"]
    assert set(factors) == {
        "short_term_reversal", "low_volatility", "relative_strength_20d",
    }
    assert factors["short_term_reversal"]["fold_count"] > 0
    assert factors["low_volatility"]["fold_count"] > 0
    assert factors["relative_strength_20d"]["fold_count"] > 0
    assert factors["short_term_reversal"]["folds"][0]["test_dates"] > 0
    assert factors["relative_strength_20d"]["selection_rule"].startswith("highest")
