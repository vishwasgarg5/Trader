from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from trader.labels import triple_barrier_labels
from trader.pipeline import (
    DATA, FEATURES as BASE_FEATURES, build_features, download_prices,
    load_universe, make_model,
)
from trader.research import add_relative_strength_features, merge_delivery_percentages, walk_forward_evaluate

EXPERIMENT_FEATURES = BASE_FEATURES + [
    "nifty_ret_10", "nifty_ret_20", "nifty_vix_change",
    "relative_ret_5", "relative_ret_10", "relative_ret_20",
    "relative_strength_rank_5", "delivery_pct",
]


def build_experiment_frame(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build triple-barrier labels and relative-strength features from OHLCV."""
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
        part["target"] = labels["target"].reindex(part.index)
        part["exit_reason"] = labels["exit_reason"].reindex(part.index)
        part["outcome_return"] = labels["outcome_return"].reindex(part.index)
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
    frame = build_experiment_frame(prices)
    labelled = frame.dropna(subset=["target"]).copy()
    if len(labelled.index.unique()) < 900:
        raise RuntimeError("At least 900 trading dates are required for 3-year walk-forward evaluation")

    # Rolling three-year training windows; each test fold is the next quarter.
    metrics = walk_forward_evaluate(
        labelled, EXPERIMENT_FEATURES, make_model,
        horizon=5, train_years=3, test_months=3,
    )
    metrics["experiment"] = "triple_barrier_relative_strength_delivery"
    metrics["target_definition"] = (
        "first touch of +2 ATR target or -1.5 ATR stop; timeout uses realised "
        "return sign; same-day double touches excluded; opening gaps executed at open"
    )
    metrics["feature_columns"] = EXPERIMENT_FEATURES
    metrics["ambiguous_rows"] = int((frame["exit_reason"] == "ambiguous").sum())
    metrics["target_rows"] = int(frame["target"].notna().sum())
    metrics["delivery_data_available"] = bool(
        (DATA / "raw" / "delivery.csv").exists()
    )

    report_dir = DATA / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "triple_barrier_experiment.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    return metrics


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2))
