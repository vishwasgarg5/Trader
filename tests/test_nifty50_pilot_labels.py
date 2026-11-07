import numpy as np
import pandas as pd
import pytest

from trader.nifty50_pilot_labels import build_fixed_horizon_labels


READY = {
    "membership_verified": True,
    "security_identity_verified": True,
    "stock_total_returns_verified": True,
    "benchmark_tri_verified": True,
    "execution_costs_verified": True,
}


def _observations(**overrides):
    row = {
        "security_id": "SEC-001",
        "signal_date": "2024-01-01",
        "entry_date": "2024-01-02",
        "exit_date": "2024-01-08",
        "entry_session_ordinal": 0,
        "exit_session_ordinal": 4,
        "stock_total_return": 0.04,
        "benchmark_tri_return": 0.01,
        "reference_cost_fraction": 0.005,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_computes_net_total_return_relative_to_matched_tri():
    result = build_fixed_horizon_labels(_observations(), **READY).iloc[0]
    expected_net = (1.04 * 0.995) - 1
    assert result["status"] == "RESOLVED"
    assert result["net_stock_return"] == pytest.approx(expected_net)
    assert result["net_relative_excess_return"] == pytest.approx(expected_net - 0.01)
    assert result["label"] == 1


def test_threshold_is_strict_and_equality_is_negative():
    # 1.5% gross less 0.5% costs = 1.0% net; TRI is zero.
    result = build_fixed_horizon_labels(
        _observations(stock_total_return=0.015, reference_cost_fraction=0.005,
                      benchmark_tri_return=0.0), **READY
    ).iloc[0]
    assert result["net_relative_excess_return"] == pytest.approx(0.01)
    assert result["label"] == 0


@pytest.mark.parametrize("flag", list(READY))
def test_any_unverified_prerequisite_leaves_label_unresolved(flag):
    flags = dict(READY)
    flags[flag] = False
    result = build_fixed_horizon_labels(_observations(), **flags).iloc[0]
    assert result["status"] == "UNRESOLVED"
    assert pd.isna(result["label"])
    assert "prerequisites_not_verified" in result["reason"]


def test_invalid_five_session_interval_is_unresolved_not_negative():
    result = build_fixed_horizon_labels(
        _observations(exit_session_ordinal=5), **READY
    ).iloc[0]
    assert result["status"] == "UNRESOLVED"
    assert pd.isna(result["label"])
    assert result["reason"] == "interval_not_exactly_five_entry_sessions"


def test_missing_returns_are_unresolved_not_negative():
    result = build_fixed_horizon_labels(
        _observations(stock_total_return=np.nan), **READY
    ).iloc[0]
    assert result["status"] == "UNRESOLVED"
    assert pd.isna(result["label"])


def test_rejects_duplicate_security_signal_date():
    frame = pd.concat([_observations(), _observations()], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate"):
        build_fixed_horizon_labels(frame, **READY)


def test_rejects_invalid_cost_fraction():
    result = build_fixed_horizon_labels(
        _observations(reference_cost_fraction=1.0), **READY
    ).iloc[0]
    assert result["status"] == "UNRESOLVED"
    assert result["reason"] == "invalid_reference_cost_fraction"


def test_no_legacy_triple_barrier_dependency():
    # The pilot's fixed-horizon target is deliberately separate from legacy labels.
    result = build_fixed_horizon_labels(_observations(), **READY)
    assert "exit_reason" not in result.columns
    assert result.iloc[0]["holding_sessions"] == 5
