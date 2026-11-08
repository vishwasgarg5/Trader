import json

import numpy as np
import pandas as pd
import pytest

from trader.exploratory_rank_experiment import (
    STATUS,
    evaluate_walk_forward,
    load_development_panel,
    make_ranked_features,
    validate_features,
)


def _panel(days=520, names=6):
    dates = pd.bdate_range("2020-01-01", periods=days)
    rows = []
    for day_index, date in enumerate(dates):
        for stock_index in range(names):
            signal = float(stock_index) / names + np.sin(day_index / 13 + stock_index) * 0.01
            rows.append({
                "signal_date": date,
                "symbol": f"S{stock_index:02d}",
                "feature_available_at": date,
                "outcome_end_date": date + pd.Timedelta(days=5),
                "net_return": signal * 0.01 + np.cos(day_index / 9 + stock_index) * 0.002,
                "ret_5": signal,
                "rsi_14": 20 + stock_index * 8,
            })
    return pd.DataFrame(rows)


def test_feature_ranks_are_calculated_within_signal_date():
    frame = _panel(days=3, names=6)
    ranked = make_ranked_features(frame, ["ret_5"])
    assert ranked.groupby("signal_date")["ret_5"].min().eq(1 / 6).all()
    assert ranked.groupby("signal_date")["ret_5"].max().eq(1.0).all()


def test_outcome_and_label_columns_cannot_be_features():
    frame = _panel(days=5)
    with pytest.raises(ValueError, match="outcome/label-like"):
        validate_features(frame, ["net_return"])
    with pytest.raises(ValueError, match="outcome/label-like"):
        validate_features(frame, ["future_price"])


def test_development_manifest_must_explicitly_exclude_holdout(tmp_path):
    csv_path = tmp_path / "panel.csv"
    manifest_path = tmp_path / "manifest.json"
    _panel(days=10).to_csv(csv_path, index=False)
    manifest = {
        "status": STATUS,
        "dataset_scope": "development_only",
        "holdout_included": True,
        "production_data_authorized": False,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="holdout_included=false"):
        load_development_panel(csv_path, manifest_path)


def test_future_feature_timestamp_is_rejected(tmp_path):
    csv_path = tmp_path / "panel.csv"
    manifest_path = tmp_path / "manifest.json"
    panel = _panel(days=10)
    panel.loc[0, "feature_available_at"] = panel.loc[0, "signal_date"] + pd.Timedelta(days=1)
    panel.to_csv(csv_path, index=False)
    manifest_path.write_text(json.dumps({
        "status": STATUS,
        "dataset_scope": "development_only",
        "holdout_included": False,
        "production_data_authorized": False,
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="future-dated"):
        load_development_panel(csv_path, manifest_path)


def test_walk_forward_is_chronological_purged_and_selects_exactly_five():
    frame = _panel(days=900, names=8)
    result = evaluate_walk_forward(
        frame, ["ret_5", "rsi_14"], train_years=1, test_months=3,
        minimum_names_per_date=8, picks_per_date=5,
    )
    assert result["status"] == "evaluated"
    assert result["fold_count"] >= 1
    for fold in result["folds"]:
        assert fold["purge_rule"] == "outcome_end_date < test_start"
        for metric in fold["metrics"].values():
            assert metric["daily_top5_count_min"] == 5
            assert metric["daily_top5_count_max"] == 5


def test_insufficient_universe_dates_fail_closed():
    frame = _panel(days=50, names=4)
    result = evaluate_walk_forward(
        frame, ["ret_5"], train_years=1, test_months=3,
        minimum_names_per_date=5, picks_per_date=5,
    )
    assert result["status"] == "insufficient_eligible_dates"
    assert result["fold_count"] == 0
