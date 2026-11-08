"""Isolated exploratory cross-sectional NIFTY 50 ranking experiment.

This module is intentionally separate from the registered pilot and production
prediction path. It accepts only a declared development-only panel, never opens
the final holdout, and marks every result as unverified-data exploration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

STATUS = "EXPLORATORY_UNVERIFIED_DATA"
REQUIRED_COLUMNS = {
    "signal_date", "symbol", "feature_available_at",
    "outcome_end_date", "net_return",
}
FORBIDDEN_FEATURE_TOKENS = (
    "target", "label", "outcome", "future", "entry_", "exit_", "net_return",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_development_panel(csv_path: Path, manifest_path: Path) -> tuple[pd.DataFrame, dict]:
    """Load a panel only when its manifest explicitly excludes the holdout."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != STATUS:
        raise ValueError(f"manifest status must be {STATUS}")
    if manifest.get("dataset_scope") != "development_only":
        raise ValueError("manifest dataset_scope must be development_only")
    if manifest.get("holdout_included") is not False:
        raise ValueError("manifest must explicitly set holdout_included=false")
    if manifest.get("production_data_authorized") is not False:
        raise ValueError("manifest must explicitly deny production-data authorization")

    frame = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"panel is missing required columns: {sorted(missing)}")
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise").dt.tz_localize(None)
    frame["feature_available_at"] = pd.to_datetime(
        frame["feature_available_at"], errors="raise"
    ).dt.tz_localize(None)
    frame["outcome_end_date"] = pd.to_datetime(
        frame["outcome_end_date"], errors="raise"
    ).dt.tz_localize(None)
    if frame[["signal_date", "symbol"]].duplicated().any():
        raise ValueError("panel contains duplicate signal_date/symbol rows")
    if (frame["feature_available_at"] > frame["signal_date"]).any():
        raise ValueError("future-dated feature availability detected")
    if (frame["outcome_end_date"] <= frame["signal_date"]).any():
        raise ValueError("outcome_end_date must be after signal_date")
    if not np.isfinite(pd.to_numeric(frame["net_return"], errors="coerce")).all():
        raise ValueError("net_return must be finite for every row")
    manifest["input_sha256"] = sha256_file(csv_path)
    manifest["input_rows"] = int(len(frame))
    manifest["input_signal_dates"] = int(frame["signal_date"].nunique())
    return frame.sort_values(["signal_date", "symbol"]).reset_index(drop=True), manifest


def validate_features(frame: pd.DataFrame, features: list[str]) -> list[str]:
    if not features:
        raise ValueError("at least one explicitly registered feature is required")
    if len(features) != len(set(features)):
        raise ValueError("feature list contains duplicates")
    missing = set(features).difference(frame.columns)
    if missing:
        raise ValueError(f"requested features are absent: {sorted(missing)}")
    forbidden = [
        name for name in features
        if any(token in name.lower() for token in FORBIDDEN_FEATURE_TOKENS)
    ]
    if forbidden:
        raise ValueError(f"outcome/label-like columns cannot be features: {forbidden}")
    return features


def make_ranked_features(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Convert each stock feature to a same-date percentile rank."""
    result = frame.copy()
    for name in features:
        values = pd.to_numeric(result[name], errors="coerce")
        result[name] = values.groupby(result["signal_date"]).rank(
            pct=True, method="average",
        )
    return result


def _make_logistic() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(C=0.1, max_iter=1500, random_state=42)),
    ])


def _make_boosting() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("model", HistGradientBoostingClassifier(
            max_iter=80, learning_rate=0.04, max_leaf_nodes=7,
            min_samples_leaf=30, l2_regularization=5.0, random_state=42,
        )),
    ])


def _daily_metrics(scored: pd.DataFrame, score_column: str, picks: int) -> dict:
    top = (
        scored.sort_values(
            ["signal_date", score_column, "symbol"],
            ascending=[True, False, True], kind="mergesort",
        ).groupby("signal_date", sort=True).head(picks)
    )
    precision = top.groupby("signal_date")["target"].mean()
    base_rate = scored.groupby("signal_date")["target"].mean()
    top_return = top.groupby("signal_date")["net_return"].mean()
    universe_return = scored.groupby("signal_date")["net_return"].mean()
    rank_ics = []
    daily_aucs = []
    for _, group in scored.groupby("signal_date", sort=True):
        if group[score_column].nunique() > 1 and group["net_return"].nunique() > 1:
            value = group[score_column].corr(group["net_return"], method="spearman")
            if pd.notna(value):
                rank_ics.append(float(value))
        if group["target"].nunique() == 2:
            daily_aucs.append(float(roc_auc_score(group["target"], group[score_column])))
    spreads = (top_return - universe_return).dropna()
    lift = precision / base_rate.replace(0, np.nan)
    return {
        "qualifying_dates": int(precision.size),
        "top5_precision": float(precision.mean()) if not precision.empty else None,
        "universe_base_rate": float(base_rate.mean()) if not base_rate.empty else None,
        "top5_precision_lift": float(lift.mean()) if lift.notna().any() else None,
        "mean_daily_rank_ic": float(np.mean(rank_ics)) if rank_ics else None,
        "mean_daily_auc": float(np.mean(daily_aucs)) if daily_aucs else None,
        "top5_mean_net_return": float(top_return.mean()) if not top_return.empty else None,
        "universe_mean_net_return": float(universe_return.mean()) if not universe_return.empty else None,
        "top5_minus_universe_mean_net_return": float(spreads.mean()) if not spreads.empty else None,
        "daily_top5_count_min": int(top.groupby("signal_date").size().min()) if not top.empty else 0,
        "daily_top5_count_max": int(top.groupby("signal_date").size().max()) if not top.empty else 0,
    }


def evaluate_walk_forward(
    frame: pd.DataFrame,
    features: list[str],
    *,
    train_years: int = 3,
    test_months: int = 3,
    minimum_names_per_date: int = 30,
    picks_per_date: int = 5,
) -> dict:
    """Chronological walk-forward evaluation with outcome-date purge.

    This evaluates only development rows supplied by the caller. It has no
    holdout-loading path and requires the outcome window to finish before each
    test fold begins.
    """
    if train_years < 1 or test_months < 1 or minimum_names_per_date < picks_per_date:
        raise ValueError("invalid walk-forward configuration")
    validate_features(frame, features)
    required = REQUIRED_COLUMNS
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"frame is missing required columns: {sorted(missing)}")

    data = frame.copy()
    data["signal_date"] = pd.to_datetime(data["signal_date"]).dt.tz_localize(None)
    data["outcome_end_date"] = pd.to_datetime(data["outcome_end_date"]).dt.tz_localize(None)
    data["net_return"] = pd.to_numeric(data["net_return"], errors="coerce")
    data = data.dropna(subset=["net_return"])
    counts = data.groupby("signal_date")["symbol"].nunique()
    eligible_dates = counts[counts >= minimum_names_per_date].index
    data = data[data["signal_date"].isin(eligible_dates)].copy()
    if data.empty:
        return {"status": "insufficient_eligible_dates", "folds": [], "fold_count": 0}

    # Daily median target is defined from outcomes, never supplied as a feature.
    daily_median = data.groupby("signal_date")["net_return"].transform("median")
    data["target"] = (data["net_return"] > daily_median).astype(int)
    data = make_ranked_features(data, features)
    dates = pd.DatetimeIndex(sorted(data["signal_date"].unique()))
    first_test = dates.min() + pd.DateOffset(years=train_years)
    last_date = dates.max()
    cursor = first_test
    folds = []

    while cursor <= last_date:
        test_end = cursor + pd.DateOffset(months=test_months)
        train_start = cursor - pd.DateOffset(years=train_years)
        train = data[
            (data["signal_date"] >= train_start)
            & (data["signal_date"] < cursor)
            & (data["outcome_end_date"] < cursor)
        ].copy()
        test = data[
            (data["signal_date"] >= cursor)
            & (data["signal_date"] < test_end)
        ].copy()
        if not train.empty and not test.empty and train["target"].nunique() == 2:
            models = {
                "regularized_logistic": _make_logistic(),
                "regularized_gradient_boosting": _make_boosting(),
            }
            predictions = {}
            for name, model in models.items():
                model.fit(train[features], train["target"].astype(int))
                predictions[name] = model.predict_proba(test[features])[:, 1]

            scored = test[["signal_date", "symbol", "target", "net_return"]].copy()
            scored["logistic_score"] = predictions["regularized_logistic"]
            scored["boost_score"] = predictions["regularized_gradient_boosting"]
            # A fixed, equal-weight score blend is a comparator, not a tuned ensemble.
            scored["ensemble_score"] = (
                scored["logistic_score"].rank(pct=True)
                + scored["boost_score"].rank(pct=True)
            ) / 2.0

            model_metrics = {
                "regularized_logistic": _daily_metrics(scored, "logistic_score", picks_per_date),
                "regularized_gradient_boosting": _daily_metrics(scored, "boost_score", picks_per_date),
                "equal_weight_rank_ensemble": _daily_metrics(scored, "ensemble_score", picks_per_date),
            }
            if "ret_5" in test.columns:
                baseline = test[["signal_date", "symbol", "target", "net_return", "ret_5"]].copy()
                baseline["previous_close_5d_momentum"] = pd.to_numeric(
                    baseline["ret_5"], errors="coerce"
                )
                model_metrics["previous_close_5d_momentum"] = _daily_metrics(
                    baseline.dropna(subset=["previous_close_5d_momentum"]),
                    "previous_close_5d_momentum", picks_per_date,
                )
            folds.append({
                "train_start": str(train["signal_date"].min().date()),
                "train_end": str(train["signal_date"].max().date()),
                "test_start": str(test["signal_date"].min().date()),
                "test_end": str(test["signal_date"].max().date()),
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "purge_rule": "outcome_end_date < test_start",
                "metrics": model_metrics,
            })
        cursor = test_end

    return {
        "status": "evaluated" if folds else "insufficient_walk_forward_history",
        "fold_count": len(folds),
        "folds": folds,
        "evaluation": "development_only_chronological_walk_forward",
        "picks_per_date": picks_per_date,
        "minimum_names_per_date": minimum_names_per_date,
        "holdout_accessed": False,
    }


def run_from_files(
    csv_path: Path,
    manifest_path: Path,
    output_path: Path,
    features: list[str],
) -> dict:
    frame, manifest = load_development_panel(csv_path, manifest_path)
    result = evaluate_walk_forward(frame, features)
    report = {
        "status": STATUS,
        "production_model_modified": False,
        "production_data_modified": False,
        "final_holdout_accessed": False,
        "holdout_access_authorized": False,
        "promotion_eligible": False,
        "paper_trading_eligible": False,
        "live_trading_eligible": False,
        "input_manifest": manifest,
        "feature_columns": features,
        "model_comparators": [
            "regularized_logistic",
            "regularized_gradient_boosting",
            "equal_weight_rank_ensemble",
            "previous_close_5d_momentum_if_available",
        ],
        "walk_forward": result,
        "interpretation": (
            "Exploratory engineering evidence only. Data authenticity, point-in-time "
            "membership, historical corporate actions, and cost assumptions are not "
            "independently verified. Do not report as verified out-of-sample accuracy."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--features", required=True, help="Comma-separated, pre-registered feature columns")
    args = parser.parse_args()
    features = [item.strip() for item in args.features.split(",") if item.strip()]
    report = run_from_files(args.input, args.manifest, args.output, features)
    print(json.dumps({
        "status": report["status"],
        "walk_forward_status": report["walk_forward"]["status"],
        "fold_count": report["walk_forward"].get("fold_count", 0),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
