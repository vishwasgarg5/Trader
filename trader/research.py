from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score


def add_relative_strength_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add market-relative momentum and same-day cross-sectional ranks."""
    required = {"symbol", "ret_5", "ret_10", "ret_20", "nifty_ret_5",
                "nifty_ret_1"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    result = frame.copy()
    for horizon in (5, 10, 20):
        market_col = f"nifty_ret_{horizon}"
        if market_col in result:
            result[f"relative_ret_{horizon}"] = result[f"ret_{horizon}"] - result[market_col]
        elif horizon == 10 or horizon == 20:
            # These Nifty horizons are derived from the daily index series
            # by the pipeline and should normally be present.
            result[f"relative_ret_{horizon}"] = np.nan
    result["relative_strength_rank_5"] = result.groupby(level=0)["ret_5"].rank(
        pct=True, method="average"
    )
    result["delivery_pct"] = pd.to_numeric(
        result.get("delivery_pct", pd.Series(np.nan, index=result.index)),
        errors="coerce",
    )
    result.loc[~result["delivery_pct"].between(0, 100), "delivery_pct"] = np.nan
    return result


def merge_delivery_percentages(
    frame: pd.DataFrame,
    path: Path,
) -> pd.DataFrame:
    """Merge optional NSE delivery data from date,symbol,delivery_pct CSV.

    This deliberately does not scrape or fabricate delivery values. Missing
    files/observations remain NaN and can be imputed by the model pipeline.
    """
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
        suffixes=("", "_source"),
    )
    merged = merged.set_index("date")
    return merged


def walk_forward_evaluate(
    frame: pd.DataFrame,
    features: list[str],
    model_factory,
    horizon: int = 5,
    train_years: int = 3,
    test_months: int = 3,
) -> dict:
    """Rolling expanding-date walk-forward evaluation with a purge gap.

    Each test window is scored independently. Top-five precision is calculated
    per test date, then averaged across dates. Dates with fewer than five
    eligible stocks use all available candidates for that date.
    """
    from pandas.tseries.offsets import BDay, DateOffset

    labelled = frame.dropna(subset=["target"]).copy()
    dates = pd.DatetimeIndex(sorted(pd.to_datetime(labelled.index.unique())))
    if len(dates) == 0:
        raise ValueError("No labelled observations for walk-forward evaluation")

    first_test = dates.min() + DateOffset(years=train_years)
    last_date = dates.max()
    fold_rows = []
    cursor = first_test
    while cursor <= last_date:
        test_end = cursor + DateOffset(months=test_months)
        train_end = cursor - BDay(horizon)
        train_start = cursor - DateOffset(years=train_years)
        train = labelled.loc[
            (labelled.index >= train_start) & (labelled.index < train_end)
        ]
        test = labelled.loc[
            (labelled.index >= cursor) & (labelled.index < test_end)
        ]
        if (not train.empty and not test.empty and train["target"].nunique() == 2):
            model = model_factory()
            model.fit(train[features], train["target"].astype(int))
            probabilities = model.predict_proba(test[features])[:, 1]
            scored = test.copy()
            scored["probability"] = probabilities
            daily_top = scored.groupby(level=0, sort=True).apply(
                lambda group: group.nlargest(min(5, len(group)), "probability")
            )
            daily_precision = daily_top.groupby(level=0)["target"].mean()
            fold = {
                "train_start": str(train.index.min().date()),
                "train_end": str(train.index.max().date()),
                "test_start": str(test.index.min().date()),
                "test_end": str(test.index.max().date()),
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "top5_precision": float(daily_precision.mean()),
                "brier_score": float(brier_score_loss(test["target"], probabilities)),
                "roc_auc": (
                    float(roc_auc_score(test["target"], probabilities))
                    if test["target"].nunique() == 2 else None
                ),
                "test_dates": int(daily_precision.size),
            }
            fold_rows.append(fold)
        cursor = test_end

    if not fold_rows:
        return {"folds": [], "fold_count": 0, "status": "insufficient_history"}
    valid_auc = [row["roc_auc"] for row in fold_rows if row["roc_auc"] is not None]
    return {
        "folds": fold_rows,
        "fold_count": len(fold_rows),
        "mean_top5_precision": float(np.mean([r["top5_precision"] for r in fold_rows])),
        "mean_brier_score": float(np.mean([r["brier_score"] for r in fold_rows])),
        "mean_roc_auc": float(np.mean(valid_auc)) if valid_auc else None,
        "status": "evaluated",
    }
