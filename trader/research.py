from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score


def add_relative_strength_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add market-relative momentum and same-day cross-sectional ranks."""
    required = {"symbol", "ret_5", "ret_10", "ret_20", "nifty_ret_5", "nifty_ret_1"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    result = frame.copy()
    for horizon in (5, 10, 20):
        market_col = f"nifty_ret_{horizon}"
        result[f"relative_ret_{horizon}"] = (
            result[f"ret_{horizon}"] - result[market_col]
            if market_col in result else np.nan
        )
    result["relative_strength_rank_5"] = result.groupby(level=0)["ret_5"].rank(
        pct=True, method="average"
    )
    result["delivery_pct"] = pd.to_numeric(
        result.get("delivery_pct", pd.Series(np.nan, index=result.index)),
        errors="coerce",
    )
    result.loc[~result["delivery_pct"].between(0, 100), "delivery_pct"] = np.nan
    return result


def merge_delivery_percentages(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Merge optional NSE delivery data from date,symbol,delivery_pct CSV."""
    result = frame.copy()
    result["delivery_pct"] = np.nan
    if not path.exists():
        return result
    delivery = pd.read_csv(path)
    required = {"date", "symbol", "delivery_pct"}
    missing = required.difference(delivery.columns)
    if missing:
        raise ValueError(f"Delivery CSV missing columns: {sorted(missing)}")
    delivery["date"] = pd.to_datetime(delivery["date"]).dt.tz_localize(None)
    delivery["symbol"] = delivery["symbol"].astype(str).str.strip().str.upper()
    delivery["delivery_pct"] = pd.to_numeric(delivery["delivery_pct"], errors="coerce")
    if delivery.duplicated(["date", "symbol"]).any():
        raise ValueError("Delivery CSV contains duplicate date/symbol rows")
    delivery.loc[~delivery["delivery_pct"].between(0, 100), "delivery_pct"] = np.nan

    left = result.drop(columns=["delivery_pct"], errors="ignore").reset_index(names="date")
    left["date"] = pd.to_datetime(left["date"]).dt.tz_localize(None)
    left["symbol"] = left["symbol"].astype(str).str.strip().str.upper()
    merged = left.merge(
        delivery[["date", "symbol", "delivery_pct"]],
        on=["date", "symbol"], how="left", validate="many_to_one",
    )
    return merged.set_index("date")


def purge_training_rows(
    frame: pd.DataFrame, cursor: pd.Timestamp, train_start: pd.Timestamp, horizon: int
) -> tuple[pd.DataFrame, str]:
    """Keep only training labels whose outcomes were known before test start."""
    candidates = frame.loc[(frame.index >= train_start) & (frame.index < cursor)]
    if "exit_date" in candidates.columns:
        exits = pd.to_datetime(candidates["exit_date"], errors="coerce")
        return candidates.loc[exits < cursor], "actual_exit_date"
    from pandas.tseries.offsets import BDay
    return candidates.loc[candidates.index < cursor - BDay(horizon)], "business_day_fallback"


def _safe_auc(target, scores):
    target = np.asarray(target)
    scores = np.asarray(scores, dtype=float)
    if len(np.unique(target)) < 2 or not np.isfinite(scores).all():
        return None
    return float(roc_auc_score(target, scores))


def _cross_sectional_auc(test: pd.DataFrame, scores: np.ndarray) -> float | None:
    scored = test[["target"]].copy()
    scored["score"] = scores
    daily = [
        value for _, group in scored.groupby(level=0, sort=True)
        if (value := _safe_auc(group["target"], group["score"])) is not None
    ]
    return float(np.mean(daily)) if daily else None


def _single_feature_aucs(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> dict:
    results = {}
    for feature in features:
        train_values = pd.to_numeric(train[feature], errors="coerce")
        median = train_values.median()
        if not np.isfinite(median):
            continue
        values = pd.to_numeric(test[feature], errors="coerce").fillna(median)
        auc = _safe_auc(test["target"], values)
        if auc is not None:
            results[feature] = auc
    return results


def walk_forward_evaluate(
    frame: pd.DataFrame,
    features: list[str],
    model_factory,
    horizon: int = 5,
    train_years: int = 3,
    test_months: int = 3,
    baseline_factory=None,
    shuffle_repeats: int = 3,
) -> dict:
    """Rolling walk-forward evaluation with outcome-date purge and diagnostics.

    Includes pooled and per-date cross-sectional AUC, flipped-score AUC,
    shuffled-training-label controls, single-feature AUCs, and optional
    logistic-regression baseline. Top-five returns are per-trade averages.
    """
    from pandas.tseries.offsets import DateOffset

    labelled = frame.dropna(subset=["target"]).copy()
    dates = pd.DatetimeIndex(sorted(pd.to_datetime(labelled.index.unique())))
    if len(dates) == 0:
        raise ValueError("No labelled observations for walk-forward evaluation")

    first_test = dates.min() + DateOffset(years=train_years)
    last_date = dates.max()
    fold_rows = []
    cursor = first_test
    fold_number = 0
    while cursor <= last_date:
        fold_number += 1
        test_end = cursor + DateOffset(months=test_months)
        train_start = cursor - DateOffset(years=train_years)
        train, purge_method = purge_training_rows(labelled, cursor, train_start, horizon)
        test = labelled.loc[(labelled.index >= cursor) & (labelled.index < test_end)]
        if not train.empty and not test.empty and train["target"].nunique() == 2:
            model = model_factory()
            model.fit(train[features], train["target"].astype(int))
            probabilities = model.predict_proba(test[features])[:, 1]
            auc = _safe_auc(test["target"], probabilities)

            scored = test.copy()
            scored["probability"] = probabilities
            daily_top = (
                scored.sort_values("probability", ascending=False)
                .groupby(level=0, sort=True).head(5)
            )
            daily_precision = daily_top.groupby(level=0)["target"].mean()
            daily_base = test.groupby(level=0)["target"].mean()
            daily_universe_gross = test.groupby(level=0)["outcome_return"].mean()
            daily_top_gross = daily_top.groupby(level=0)["outcome_return"].mean()
            daily_universe_net = (
                test.groupby(level=0)["net_return"].mean() if "net_return" in test else None
            )
            daily_top_net = (
                daily_top.groupby(level=0)["net_return"].mean()
                if "net_return" in daily_top else None
            )

            shuffled_aucs = []
            target_values = train["target"].astype(int).to_numpy()
            for repeat in range(shuffle_repeats):
                rng = np.random.default_rng(4200 + fold_number * 101 + repeat)
                shuffled = rng.permutation(target_values)
                null_model = model_factory()
                null_model.fit(train[features], shuffled)
                null_scores = null_model.predict_proba(test[features])[:, 1]
                null_auc = _safe_auc(test["target"], null_scores)
                if null_auc is not None:
                    shuffled_aucs.append(null_auc)

            logistic_auc = None
            if baseline_factory is not None:
                baseline = baseline_factory()
                baseline.fit(train[features], train["target"].astype(int))
                logistic_auc = _safe_auc(
                    test["target"], baseline.predict_proba(test[features])[:, 1]
                )

            feature_aucs = _single_feature_aucs(train, test, features)
            base_rate = float(daily_base.mean())
            fold_rows.append({
                "train_start": str(train.index.min().date()),
                "train_end": str(train.index.max().date()),
                "test_start": str(test.index.min().date()),
                "test_end": str(test.index.max().date()),
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "purge_method": purge_method,
                "top5_precision": float(daily_precision.mean()),
                "base_rate": base_rate,
                "top5_precision_lift": float(daily_precision.mean() / base_rate) if base_rate > 0 else None,
                "top5_mean_gross_return": float(daily_top_gross.mean()),
                "universe_mean_gross_return": float(daily_universe_gross.mean()),
                "top5_mean_net_return": float(daily_top_net.mean()) if daily_top_net is not None else None,
                "universe_mean_net_return": float(daily_universe_net.mean()) if daily_universe_net is not None else None,
                "brier_score": float(brier_score_loss(test["target"], probabilities)),
                "roc_auc": auc,
                "flipped_roc_auc": (1.0 - auc) if auc is not None else None,
                "cross_sectional_auc": _cross_sectional_auc(test, probabilities),
                "shuffled_label_auc_mean": float(np.mean(shuffled_aucs)) if shuffled_aucs else None,
                "shuffled_label_auc_runs": shuffled_aucs,
                "logistic_regression_auc": logistic_auc,
                "single_feature_auc": feature_aucs,
                "test_dates": int(daily_precision.size),
            })
        cursor = test_end

    if not fold_rows:
        return {"folds": [], "fold_count": 0, "status": "insufficient_history"}
    def mean_metric(key):
        values = [row[key] for row in fold_rows if row.get(key) is not None]
        return float(np.mean(values)) if values else None

    feature_names = sorted({name for row in fold_rows for name in row["single_feature_auc"]})
    return {
        "folds": fold_rows,
        "fold_count": len(fold_rows),
        "mean_top5_precision": mean_metric("top5_precision"),
        "mean_base_rate": mean_metric("base_rate"),
        "mean_top5_precision_lift": mean_metric("top5_precision_lift"),
        "mean_top5_gross_return": mean_metric("top5_mean_gross_return"),
        "mean_universe_gross_return": mean_metric("universe_mean_gross_return"),
        "mean_top5_net_return": mean_metric("top5_mean_net_return"),
        "mean_universe_net_return": mean_metric("universe_mean_net_return"),
        "mean_brier_score": mean_metric("brier_score"),
        "mean_roc_auc": mean_metric("roc_auc"),
        "mean_flipped_roc_auc": mean_metric("flipped_roc_auc"),
        "mean_cross_sectional_auc": mean_metric("cross_sectional_auc"),
        "mean_shuffled_label_auc": mean_metric("shuffled_label_auc_mean"),
        "mean_logistic_regression_auc": mean_metric("logistic_regression_auc"),
        "mean_single_feature_auc": {
            feature: float(np.mean([
                row["single_feature_auc"][feature]
                for row in fold_rows if feature in row["single_feature_auc"]
            ]))
            for feature in feature_names
        },
        "status": "evaluated",
    }
