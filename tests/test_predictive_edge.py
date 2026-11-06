import pytest

from trader.predictive_edge import summarize_predictive_edge


def test_predictive_edge_compares_model_logistic_and_shuffled_controls():
    folds = []
    for index in range(8):
        folds.append({
            "test_start": f"2024-{index + 1:02d}-01",
            "test_end": f"2024-{index + 1:02d}-28",
            "cross_sectional_auc": 0.54,
            "logistic_regression_cross_sectional_auc": 0.52,
            "shuffled_label_auc_runs": [0.49] * 99,
        })
    result = summarize_predictive_edge({"folds": folds}, repeats=300)
    assert result["fold_count"] == 8
    assert result["folds_model_auc_above_logistic"] == 8
    assert result["mean_model_minus_logistic_cross_sectional_auc"] == pytest.approx(0.02)
    assert result["folds_model_auc_above_shuffled_null_95th_percentile"] == 8
    assert result["folds_shuffled_label_p_below_0_05"] == 8
    assert result["model_minus_logistic_auc_block_bootstrap_95pct"]["lower"] > 0
    assert result["shuffled_repeats_per_fold"] == 99


def test_predictive_edge_handles_missing_comparator_and_shuffle_runs():
    result = summarize_predictive_edge({
        "folds": [{
            "test_start": "2024-01-01",
            "test_end": "2024-03-31",
            "cross_sectional_auc": 0.51,
            "logistic_regression_cross_sectional_auc": None,
            "shuffled_label_auc_runs": [],
        }]
    })
    assert result["mean_model_minus_logistic_cross_sectional_auc"] is None
    assert result["model_minus_logistic_auc_block_bootstrap_95pct"] is None
    assert result["folds_shuffled_label_p_below_0_05"] == 0



def test_research_continuation_gate_requires_absolute_profitability_and_verified_data():
    from trader.predictive_edge import evaluate_research_continuation_gate

    cross = {
        "fold_count": 8,
        "folds_with_positive_net_excess": 7,
        "top5_minus_universe_net_return_block_bootstrap_95pct": {
            "method": "circular_moving_block_bootstrap",
            "confidence_level": 0.95,
            "lower": 0.001,
            "upper": 0.004,
        },
        "mean_top5_net_return": 0.002,
    }
    edge = {"model_minus_logistic_auc_block_bootstrap_95pct": {
        "method": "circular_moving_block_bootstrap_over_walk_forward_folds",
        "confidence_level": 0.95,
        "lower": 0.001,
        "upper": 0.03,
    }}
    passed = evaluate_research_continuation_gate(
        cross, 7, edge, point_in_time_universe_verified=True,
        corporate_action_adjustments_verified=True,
    )
    assert passed["status"] == "PASS"
    assert passed["continue_price_feature_research_only"] is True

    blocked = evaluate_research_continuation_gate(
        {**cross, "mean_top5_net_return": -0.001}, 7, edge,
        point_in_time_universe_verified=False,
        corporate_action_adjustments_verified=False,
    )
    assert blocked["status"] == "STOP"
    assert "absolute_net_profitability_positive" in blocked["failed_checks"]
    assert "point_in_time_universe_verified" in blocked["failed_checks"]
    assert blocked["promotion_eligible"] is False
    assert blocked["live_execution_enabled"] is False


def test_research_continuation_gate_rejects_confidence_interval_touching_zero():
    from trader.predictive_edge import evaluate_research_continuation_gate

    cross = {
        "fold_count": 6,
        "folds_with_positive_net_excess": 5,
        "top5_minus_universe_net_return_block_bootstrap_95pct": {
            "method": "circular_moving_block_bootstrap",
            "confidence_level": 0.95,
            "lower": 0.0,
            "upper": 0.02,
        },
        "mean_top5_net_return": 0.01,
    }
    edge = {"model_minus_logistic_auc_block_bootstrap_95pct": {
        "method": "circular_moving_block_bootstrap_over_walk_forward_folds",
        "confidence_level": 0.95,
        "lower": -0.001,
        "upper": 0.01,
    }}
    result = evaluate_research_continuation_gate(
        cross, 5, edge, point_in_time_universe_verified=True,
        corporate_action_adjustments_verified=True,
    )
    assert result["status"] == "STOP"
    assert "relative_excess_95pct_interval_valid_and_above_zero" in result["failed_checks"]
    assert "incremental_auc_vs_logistic_statistically_positive" in result["failed_checks"]



def test_research_gate_rejects_relative_excess_interval_crossing_zero():
    from trader.predictive_edge import evaluate_research_continuation_gate

    cross = {
        "fold_count": 8,
        "folds_with_positive_net_excess": 8,
        "top5_minus_universe_net_return_block_bootstrap_95pct": {
            "method": "circular_moving_block_bootstrap",
            "confidence_level": 0.95,
            "lower": -0.09,
            "upper": 0.12,
        },
        "mean_top5_net_return": 0.02,
    }
    edge = {"model_minus_logistic_auc_block_bootstrap_95pct": {
        "method": "circular_moving_block_bootstrap_over_walk_forward_folds",
        "confidence_level": 0.95,
        "lower": 0.001,
        "upper": 0.02,
    }}
    result = evaluate_research_continuation_gate(
        cross, 8, edge, point_in_time_universe_verified=True,
        corporate_action_adjustments_verified=True,
    )
    assert result["status"] == "STOP"
    assert result["checks"]["relative_excess_95pct_interval_valid_and_above_zero"] is False
    assert "relative_excess_95pct_interval_valid_and_above_zero" in result["failed_checks"]
    assert result["promotion_eligible"] is False
    assert result["live_execution_enabled"] is False


def test_research_gate_rejects_malformed_or_wrong_bootstrap_interval():
    from trader.predictive_edge import is_positive_95pct_block_bootstrap_ci

    assert not is_positive_95pct_block_bootstrap_ci(
        {"method": "circular_moving_block_bootstrap", "confidence_level": 0.95,
         "lower": 0.01, "upper": -0.01},
        expected_method="circular_moving_block_bootstrap",
    )
    assert not is_positive_95pct_block_bootstrap_ci(
        {"method": "ordinary_iid_bootstrap", "confidence_level": 0.95,
         "lower": 0.01, "upper": 0.02},
        expected_method="circular_moving_block_bootstrap",
    )
    assert not is_positive_95pct_block_bootstrap_ci(
        {"method": "circular_moving_block_bootstrap", "confidence_level": 0.95,
         "lower": 0.01},
        expected_method="circular_moving_block_bootstrap",
    )
