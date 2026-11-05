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
            "shuffled_label_auc_runs": [0.49, 0.50, 0.51, 0.48, 0.50],
        })
    result = summarize_predictive_edge({"folds": folds}, repeats=300)
    assert result["fold_count"] == 8
    assert result["folds_model_auc_above_logistic"] == 8
    assert result["mean_model_minus_logistic_cross_sectional_auc"] == pytest.approx(0.02)
    assert result["folds_model_auc_above_shuffled_null_95th_percentile"] == 8
    assert result["folds_shuffled_label_p_below_0_05"] == 8
    assert result["model_minus_logistic_auc_block_bootstrap_95pct"]["lower"] > 0
    assert result["shuffled_repeats_per_fold"] == 5


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
