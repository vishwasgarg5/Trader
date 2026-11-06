from __future__ import annotations

import numpy as np


def summarize_predictive_edge(fold_metrics: dict, *, repeats: int = 5000, seed: int = 42061) -> dict:
    """Compare cross-sectional boosting with logistic and shuffled-label controls.

    Fold-level paired AUC differences are resampled in circular two-fold blocks.
    Shuffled-label p-values are one-sided empirical tests within each test fold.
    These diagnostics are evidence checks, not a strategy promotion rule.
    """
    folds = fold_metrics.get("folds", [])
    rows = []
    for fold in folds:
        model_auc = fold.get("cross_sectional_auc")
        logistic_auc = fold.get("logistic_regression_cross_sectional_auc")
        null_aucs = [
            float(value) for value in fold.get("shuffled_label_auc_runs", [])
            if value is not None and np.isfinite(value)
        ]
        p_value = None
        null_mean = None
        null_q95 = None
        if model_auc is not None and null_aucs:
            p_value = float((1 + sum(value >= model_auc for value in null_aucs)) / (len(null_aucs) + 1))
            null_mean = float(np.mean(null_aucs))
            null_q95 = float(np.quantile(null_aucs, 0.95))
        difference = (
            float(model_auc - logistic_auc)
            if model_auc is not None and logistic_auc is not None else None
        )
        rows.append({
            "test_start": fold.get("test_start"),
            "test_end": fold.get("test_end"),
            "model_cross_sectional_auc": model_auc,
            "logistic_cross_sectional_auc": logistic_auc,
            "model_minus_logistic_auc": difference,
            "shuffled_auc_mean": null_mean,
            "shuffled_auc_95th_percentile": null_q95,
            "shuffled_label_empirical_p_value": p_value,
            "shuffled_repeats": len(null_aucs),
        })

    paired = np.asarray([
        row["model_minus_logistic_auc"] for row in rows
        if row["model_minus_logistic_auc"] is not None
    ], dtype=float)
    paired = paired[np.isfinite(paired)]
    ci = None
    if len(paired) >= 4:
        rng = np.random.default_rng(seed)
        block_length = 2
        n_blocks = int(np.ceil(len(paired) / block_length))
        offsets = np.arange(block_length)
        estimates = np.empty(repeats, dtype=float)
        for index in range(repeats):
            starts = rng.integers(0, len(paired), size=n_blocks)
            sample = np.concatenate([
                paired[(start + offsets) % len(paired)] for start in starts
            ])[:len(paired)]
            estimates[index] = sample.mean()
        ci = {
            "method": "circular_moving_block_bootstrap_over_walk_forward_folds",
            "block_length_folds": block_length,
            "repeats": repeats,
            "confidence_level": 0.95,
            "lower": float(np.quantile(estimates, 0.025)),
            "upper": float(np.quantile(estimates, 0.975)),
        }

    valid_p = [
        row["shuffled_label_empirical_p_value"] for row in rows
        if row["shuffled_label_empirical_p_value"] is not None
    ]
    null_valid = [
        row for row in rows
        if row["model_cross_sectional_auc"] is not None
        and row["shuffled_auc_95th_percentile"] is not None
    ]
    return {
        "description": "Paired cross-sectional AUC comparison against logistic regression and per-fold shuffled-training-label null models.",
        "fold_count": len(rows),
        "folds_model_auc_above_logistic": int(sum(
            row["model_minus_logistic_auc"] is not None and row["model_minus_logistic_auc"] > 0
            for row in rows
        )),
        "mean_model_minus_logistic_cross_sectional_auc": float(paired.mean()) if len(paired) else None,
        "model_minus_logistic_auc_block_bootstrap_95pct": ci,
        "folds_model_auc_above_shuffled_null_95th_percentile": int(sum(
            row["model_cross_sectional_auc"] > row["shuffled_auc_95th_percentile"]
            for row in null_valid
        )),
        "mean_shuffled_label_empirical_p_value": float(np.mean(valid_p)) if valid_p else None,
        "folds_shuffled_label_p_below_0_05": int(sum(value < 0.05 for value in valid_p)),
        "shuffled_repeats_per_fold": min(
            (row["shuffled_repeats"] for row in rows), default=0
        ),
        "folds": rows,
        "interpretation_guardrail": "A positive AUC difference or low shuffle p-value is predictive evidence only; it does not establish positive net returns or justify deployment.",
    }
