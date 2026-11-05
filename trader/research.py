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
    shuffle_within_date: bool = False,
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
    daily_return_spreads = []
    portfolio_candidates = []
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
            required_portfolio_columns = {"symbol", "entry_date", "exit_date", "entry_price", "exit_price", "net_return"}
            if required_portfolio_columns.issubset(daily_top.columns):
                selected_candidates = daily_top.copy()
                selected_candidates["score"] = selected_candidates["probability"]
                portfolio_candidates.append(selected_candidates)
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
            fold_net_excess = None
            if daily_top_net is not None and daily_universe_net is not None:
                daily_spread = (daily_top_net - daily_universe_net).dropna()
                daily_return_spreads.extend(daily_spread.to_numpy(dtype=float).tolist())
                if not daily_spread.empty:
                    fold_net_excess = float(daily_spread.mean())

            shuffled_aucs = []
            target_values = train["target"].astype(int).to_numpy()
            for repeat in range(shuffle_repeats):
                rng = np.random.default_rng(4200 + fold_number * 101 + repeat)
                if shuffle_within_date:
                    shuffled = train["target"].astype(int).groupby(level=0, sort=False).transform(
                        lambda values: rng.permutation(values.to_numpy())
                    ).to_numpy()
                else:
                    shuffled = rng.permutation(target_values)
                null_model = model_factory()
                null_model.fit(train[features], shuffled)
                null_scores = null_model.predict_proba(test[features])[:, 1]
                null_auc = _safe_auc(test["target"], null_scores)
                if null_auc is not None:
                    shuffled_aucs.append(null_auc)

            logistic_auc = None
            logistic_cross_sectional_auc = None
            if baseline_factory is not None:
                baseline = baseline_factory()
                baseline.fit(train[features], train["target"].astype(int))
                logistic_scores = baseline.predict_proba(test[features])[:, 1]
                logistic_auc = _safe_auc(test["target"], logistic_scores)
                logistic_cross_sectional_auc = _cross_sectional_auc(test, logistic_scores)

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
                "top5_minus_universe_mean_net_return": fold_net_excess,
                "brier_score": float(brier_score_loss(test["target"], probabilities)),
                "roc_auc": auc,
                "flipped_roc_auc": (1.0 - auc) if auc is not None else None,
                "cross_sectional_auc": _cross_sectional_auc(test, probabilities),
                "shuffled_label_auc_mean": float(np.mean(shuffled_aucs)) if shuffled_aucs else None,
                "shuffled_label_auc_runs": shuffled_aucs,
                "logistic_regression_auc": logistic_auc,
                "logistic_regression_cross_sectional_auc": logistic_cross_sectional_auc,
                "single_feature_auc": feature_aucs,
                "test_dates": int(daily_precision.size),
                "regime_performance": summarize_regime_performance(test, daily_top) if {"nifty_above_200dma", "india_vix_low_20"}.issubset(test.columns) and "net_return" in test else None,
            })
        cursor = test_end

    if not fold_rows:
        return {"folds": [], "fold_count": 0, "status": "insufficient_history"}
    def mean_metric(key):
        values = [row[key] for row in fold_rows if row.get(key) is not None]
        return float(np.mean(values)) if values else None

    feature_names = sorted({name for row in fold_rows for name in row["single_feature_auc"]})
    portfolio_backtest = None
    if portfolio_candidates:
        from trader.portfolio import simulate_overlapping_portfolio
        portfolio_frame = pd.concat(portfolio_candidates).sort_index()
        portfolio_backtest = simulate_overlapping_portfolio(portfolio_frame)
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
        "mean_logistic_regression_cross_sectional_auc": mean_metric("logistic_regression_cross_sectional_auc"),
        "folds_auc_above_0_5": int(sum(row["roc_auc"] is not None and row["roc_auc"] > 0.5 for row in fold_rows)),
        "folds_cross_sectional_auc_above_0_5": int(sum(row["cross_sectional_auc"] is not None and row["cross_sectional_auc"] > 0.5 for row in fold_rows)),
        "folds_logistic_auc_above_0_5": int(sum(row["logistic_regression_auc"] is not None and row["logistic_regression_auc"] > 0.5 for row in fold_rows)),
        "folds_logistic_cross_sectional_auc_above_0_5": int(sum(row["logistic_regression_cross_sectional_auc"] is not None and row["logistic_regression_cross_sectional_auc"] > 0.5 for row in fold_rows)),
        "folds_with_positive_net_excess": int(sum(row["top5_minus_universe_mean_net_return"] is not None and row["top5_minus_universe_mean_net_return"] > 0 for row in fold_rows)),
        "mean_top5_minus_universe_net_return": float(np.mean(daily_return_spreads)) if daily_return_spreads else None,
        "top5_minus_universe_net_return_block_bootstrap_95pct": block_bootstrap_mean_ci(daily_return_spreads),
        "mean_single_feature_auc": {
            feature: float(np.mean([
                row["single_feature_auc"][feature]
                for row in fold_rows if feature in row["single_feature_auc"]
            ]))
            for feature in feature_names
        },
        "portfolio_backtest": portfolio_backtest,
        "status": "evaluated",
    }


def summarize_outcome_reasons(frame: pd.DataFrame) -> dict:
    """Summarize barrier and timeout outcomes separately, including costs."""
    required = {"exit_reason", "outcome_return"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    result = {}
    for reason, group in frame.groupby("exit_reason", dropna=False, sort=True):
        gross = pd.to_numeric(group["outcome_return"], errors="coerce").dropna()
        item = {
            "rows": int(len(group)),
            "mean_gross_return": float(gross.mean()) if not gross.empty else None,
            "median_gross_return": float(gross.median()) if not gross.empty else None,
            "gross_positive_fraction": float((gross > 0).mean()) if not gross.empty else None,
        }
        if "net_return" in group:
            net = pd.to_numeric(group["net_return"], errors="coerce").dropna()
            item.update({
                "mean_net_return": float(net.mean()) if not net.empty else None,
                "net_positive_fraction": float((net > 0).mean()) if not net.empty else None,
            })
        result[str(reason)] = item
    return result


CROSS_SECTIONAL_EXCLUDED_FEATURES = {
    "nifty_ret_1", "nifty_ret_5", "nifty_ret_10", "nifty_ret_20",
    "nifty_vix", "nifty_vix_change", "nifty_close", "nifty_sma_200",
    "nifty_above_200dma", "india_vix", "india_vix_low_20",
}


def make_cross_sectional_frame(frame: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Rank stock features within each date and label outperformance vs daily median."""
    if "net_return" not in frame:
        raise ValueError("Missing required columns: ['net_return']")
    result = frame.copy()
    eligible = [name for name in features if name in result.columns and name not in CROSS_SECTIONAL_EXCLUDED_FEATURES]
    if not eligible:
        raise ValueError("No stock-level features available for cross-sectional model")
    for name in eligible:
        values = pd.to_numeric(result[name], errors="coerce")
        result[name] = values.groupby(level=0).rank(pct=True, method="average")
    net = pd.to_numeric(result["net_return"], errors="coerce")
    daily_median = net.groupby(level=0).transform("median")
    result["target"] = np.where(net.notna() & daily_median.notna(), (net > daily_median).astype(float), np.nan)
    return result, eligible


def block_bootstrap_mean_ci(values, block_length: int = 5, repeats: int = 2000, seed: int = 42052) -> dict | None:
    """Circular moving-block bootstrap CI for daily portfolio spreads."""
    data = np.asarray(values, dtype=float)
    data = data[np.isfinite(data)]
    if len(data) < max(10, block_length * 2):
        return None
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(len(data) / block_length))
    estimates = np.empty(repeats, dtype=float)
    offsets = np.arange(block_length)
    for i in range(repeats):
        starts = rng.integers(0, len(data), size=n_blocks)
        sample = np.concatenate([data[(start + offsets) % len(data)] for start in starts])[:len(data)]
        estimates[i] = sample.mean()
    return {
        "method": "circular_moving_block_bootstrap",
        "block_length_trading_days": int(block_length),
        "repeats": int(repeats),
        "confidence_level": 0.95,
        "lower": float(np.quantile(estimates, 0.025)),
        "upper": float(np.quantile(estimates, 0.975)),
    }


def summarize_regime_performance(test: pd.DataFrame, daily_top: pd.DataFrame) -> dict:
    """Compare existing top-five and universe returns across predeclared market regimes."""
    if not {"net_return", "nifty_above_200dma", "india_vix_low_20"}.issubset(test.columns):
        return {}
    rows = test[["net_return", "nifty_above_200dma", "india_vix_low_20"]].copy()
    if "symbol" in test.columns and "symbol" in daily_top.columns:
        selected = set(zip(daily_top.index, daily_top["symbol"]))
        rows["top5_selected"] = [key in selected for key in zip(test.index, test["symbol"])]
    else:
        rows["top5_selected"] = False
    above = rows["nifty_above_200dma"].fillna(False).astype(bool)
    low_vix = rows["india_vix_low_20"].fillna(False).astype(bool)
    rows["regime"] = np.select(
        [above & low_vix, above & ~low_vix, ~above & low_vix],
        ["nifty_above_200dma_vix_below_20", "nifty_above_200dma_vix_at_or_above_20", "nifty_at_or_below_200dma_vix_below_20"],
        default="nifty_at_or_below_200dma_vix_at_or_above_20",
    )
    output = {}
    for regime, group in rows.groupby("regime", sort=True):
        daily_universe = group.groupby(level=0)["net_return"].mean()
        daily_top = group.loc[group["top5_selected"]].groupby(level=0)["net_return"].mean()
        paired = pd.concat([daily_top.rename("top5"), daily_universe.rename("universe")], axis=1).dropna()
        output[regime] = {
            "days": int(len(paired)),
            "top5_mean_net_return": float(paired["top5"].mean()) if not paired.empty else None,
            "universe_mean_net_return": float(paired["universe"].mean()) if not paired.empty else None,
            "top5_minus_universe": float((paired["top5"] - paired["universe"]).mean()) if not paired.empty else None,
        }
    return output


def evaluate_simple_factor_baselines(
    frame: pd.DataFrame,
    *,
    horizon: int = 5,
    train_years: int = 3,
    test_months: int = 3,
    picks_per_day: int = 5,
) -> dict:
    """Evaluate fixed, untrained cross-sectional factors on the model's OOS dates.

    Input factor columns must already be ranked within each date using only
    signal-day information. The three predeclared rules are: short-term
    reversal (lowest 5-session return), low volatility (lowest ATR%), and
    relative strength (highest 20-session market-relative return).
    """
    from pandas.tseries.offsets import DateOffset

    required = {"net_return", "ret_5", "atr_pct", "relative_ret_20"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    labelled = frame.dropna(subset=["net_return"]).copy()
    dates = pd.DatetimeIndex(sorted(pd.to_datetime(labelled.index.unique())))
    if len(dates) == 0:
        raise ValueError("No dated observations for factor baseline evaluation")

    # These are fixed before inspecting outcomes; all inputs are same-day
    # cross-sectional percentiles produced by make_cross_sectional_frame.
    factor_scores = {
        "short_term_reversal": lambda x: -pd.to_numeric(x["ret_5"], errors="coerce"),
        "low_volatility": lambda x: -pd.to_numeric(x["atr_pct"], errors="coerce"),
        "relative_strength_20d": lambda x: pd.to_numeric(x["relative_ret_20"], errors="coerce"),
    }
    cursor = dates.min() + DateOffset(years=train_years)
    last_date = dates.max()
    output = {}
    while cursor <= last_date:
        test_end = cursor + DateOffset(months=test_months)
        test = labelled.loc[(labelled.index >= cursor) & (labelled.index < test_end)]
        if not test.empty:
            for name, score_fn in factor_scores.items():
                scored = test.copy()
                scored["_factor_score"] = score_fn(scored)
                scored = scored.dropna(subset=["_factor_score", "net_return"])
                daily_top = (
                    scored.sort_values("_factor_score", ascending=False, kind="mergesort")
                    .groupby(level=0, sort=True).head(picks_per_day)
                )
                top_daily = daily_top.groupby(level=0)["net_return"].mean()
                universe_daily = scored.groupby(level=0)["net_return"].mean()
                paired = pd.concat(
                    [top_daily.rename("top"), universe_daily.rename("universe")],
                    axis=1,
                ).dropna()
                fold = {
                    "test_start": str(test.index.min().date()),
                    "test_end": str(test.index.max().date()),
                    "test_dates": int(len(paired)),
                    "top5_mean_net_return": float(paired["top"].mean()) if not paired.empty else None,
                    "universe_mean_net_return": float(paired["universe"].mean()) if not paired.empty else None,
                    "top5_minus_universe_mean_net_return": float((paired["top"] - paired["universe"]).mean()) if not paired.empty else None,
                }
                output.setdefault(name, {"folds": [], "daily_spreads": []})
                output[name]["folds"].append(fold)
                output[name]["daily_spreads"].extend(
                    (paired["top"] - paired["universe"]).to_numpy(dtype=float).tolist()
                )

        cursor = test_end

    results = {}
    for name, item in output.items():
        folds = item["folds"]
        spreads = [row["top5_minus_universe_mean_net_return"] for row in folds
                   if row["top5_minus_universe_mean_net_return"] is not None]
        top_returns = [row["top5_mean_net_return"] for row in folds
                       if row["top5_mean_net_return"] is not None]
        results[name] = {
            "folds": folds,
            "fold_count": len(folds),
            "folds_with_positive_net_excess": int(sum(value > 0 for value in spreads)),
            "mean_top5_net_return": float(np.mean(top_returns)) if top_returns else None,
            "mean_top5_minus_universe_net_return": float(np.mean(item["daily_spreads"])) if item["daily_spreads"] else None,
            "net_excess_block_bootstrap_95pct": block_bootstrap_mean_ci(item["daily_spreads"]),
            "selection_rule": {
                "short_term_reversal": "lowest same-day cross-sectional percentile of ret_5",
                "low_volatility": "lowest same-day cross-sectional percentile of atr_pct",
                "relative_strength_20d": "highest same-day cross-sectional percentile of relative_ret_20",
            }[name],
        }
    return {
        "description": "Fixed, non-trained top-five factor portfolios evaluated on the same chronological test windows as the ML model; returns are net of the supplied cost model.",
        "factor_results": results,
        "selection_note": "Factor columns must be same-day cross-sectional ranks; ties use stable input order. These are diagnostics, not optimized or promoted strategies.",
    }
