from __future__ import annotations

import json

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from trader.costs import DEFAULT_DELIVERY_COSTS, add_delivery_costs
from trader.delivery import download_delivery_history
from trader.labels import triple_barrier_labels
from trader.pipeline import (
    DATA, FEATURES as BASE_FEATURES, build_features, download_prices,
    load_universe, make_model,
)
from trader.research import (
    add_relative_strength_features, merge_delivery_percentages,
    summarize_outcome_reasons, walk_forward_evaluate,
)

EXPERIMENT_FEATURES = BASE_FEATURES + [
    "nifty_ret_10", "nifty_ret_20", "nifty_vix_change",
    "relative_ret_5", "relative_ret_10", "relative_ret_20",
    "relative_strength_rank_5", "delivery_pct",
]


def make_logistic_model() -> Pipeline:
    """Regularized linear baseline with train-only median imputation."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
        ("classifier", LogisticRegression(C=0.1, max_iter=1500, random_state=42)),
    ])


def build_experiment_frame(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build next-open triple-barrier labels and relative-strength features."""
    frame = build_features(prices)
    pieces = []
    for symbol, stock in prices.items():
        if symbol.startswith("^") or symbol not in set(frame["symbol"]):
            continue
        atr = frame.loc[frame["symbol"] == symbol, "atr"]
        bars = stock[["open", "high", "low", "close"]].copy()
        bars["atr"] = atr.reindex(bars.index)
        labels = triple_barrier_labels(bars, horizon=5)
        part = frame.loc[frame["symbol"] == symbol].copy()
        for column in (
            "target", "entry_date", "entry_price", "exit_reason",
            "exit_date", "exit_price", "outcome_return",
        ):
            part[column] = labels[column].reindex(part.index)
        pieces.append(part)

    if not pieces:
        raise RuntimeError("No stock rows available for triple-barrier experiment")
    result = pd.concat(pieces).sort_index()
    nifty = prices["^NSEI"]["close"]
    vix = prices.get("^INDIAVIX", pd.DataFrame()).get("close", pd.Series(dtype=float))
    result["nifty_ret_10"] = nifty.pct_change(10).reindex(result.index)
    result["nifty_ret_20"] = nifty.pct_change(20).reindex(result.index)
    result["nifty_vix_change"] = vix.pct_change(1).reindex(result.index)
    result = merge_delivery_percentages(result, DATA / "raw" / "delivery.csv")
    return add_relative_strength_features(result)


def run_experiment() -> dict:
    prices = download_prices(load_universe(), period="7y")
    delivery_status = download_delivery_history(prices, DATA / "raw" / "delivery.csv")
    frame = build_experiment_frame(prices)
    labelled = frame.dropna(subset=["target"]).copy()
    if len(labelled.index.unique()) < 900:
        raise RuntimeError("At least 900 trading dates are required for 3-year walk-forward evaluation")

    labelled = add_delivery_costs(labelled, **DEFAULT_DELIVERY_COSTS)
    metrics = walk_forward_evaluate(
        labelled, EXPERIMENT_FEATURES, make_model,
        horizon=5, train_years=3, test_months=3,
        baseline_factory=make_logistic_model, shuffle_repeats=3,
    )
    # Diagnose whether timeout sign-labels dilute barrier outcomes, and
    # whether a cost-aware positive-return target changes out-of-sample results.
    barrier_rows = labelled["exit_reason"].isin(["target", "target_gap", "stop", "stop_gap"])
    barrier_frame = labelled.loc[barrier_rows].copy()
    barrier_metrics = walk_forward_evaluate(
        barrier_frame, EXPERIMENT_FEATURES, make_model,
        horizon=5, train_years=3, test_months=3,
        baseline_factory=make_logistic_model, shuffle_repeats=0,
    )
    net_frame = labelled.loc[labelled["net_return"].notna()].copy()
    net_frame["target"] = (net_frame["net_return"] > 0).astype(int)
    net_metrics = walk_forward_evaluate(
        net_frame, EXPERIMENT_FEATURES, make_model,
        horizon=5, train_years=3, test_months=3,
        baseline_factory=make_logistic_model, shuffle_repeats=0,
    )
    metrics["outcome_reason_summary"] = summarize_outcome_reasons(labelled)
    metrics["target_definition_comparisons"] = {
        "barrier_only": {
            "description": "Exclude timeout outcomes; classify target-barrier exits as 1 and stop-barrier exits as 0.",
            "rows": int(len(barrier_frame)),
            "fold_metrics": barrier_metrics,
        },
        "net_positive": {
            "description": "Classify realised trade net_return > 0 as 1, otherwise 0; includes timeouts.",
            "rows": int(len(net_frame)),
            "fold_metrics": net_metrics,
        },
    }
    metrics["experiment"] = "triple_barrier_relative_strength_delivery"
    metrics["target_definition"] = (
        "signal-day features; next-session-open entry; first touch of +2 ATR "
        "target or -1.5 ATR stop; timeout uses realised return sign; "
        "same-day double touches excluded; opening gaps executed at open"
    )
    metrics["feature_columns"] = EXPERIMENT_FEATURES
    metrics["ambiguous_rows"] = int((frame["exit_reason"] == "ambiguous").sum())
    metrics["target_rows"] = int(frame["target"].notna().sum())
    metrics["delivery_data_available"] = bool(frame["delivery_pct"].notna().any())
    metrics["delivery_coverage_fraction"] = float(frame["delivery_pct"].notna().mean())
    metrics["delivery_download"] = delivery_status
    metrics["cost_assumptions"] = DEFAULT_DELIVERY_COSTS
    metrics["cost_note"] = (
        "Illustrative NSE cash-delivery statutory rates as checked 2026-11-05; "
        "2 bps slippage per side is a configurable scenario assumption, not an observed fill. "
        "Brokerage and DP charges default to zero and must be set for the user's broker."
    )

    report_dir = DATA / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "triple_barrier_experiment.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    return metrics


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2))
