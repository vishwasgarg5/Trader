from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from trader.costs import DEFAULT_DELIVERY_COSTS, add_delivery_costs
from trader.data_snapshot import write_data_snapshot_manifest
from trader.corporate_actions import audit_corporate_action_ledger
from trader.membership_evidence import audit_membership_evidence
from trader.delivery import download_delivery_history
from trader.labels import triple_barrier_labels
from trader.pipeline import (
    DATA, FEATURES as BASE_FEATURES, build_features, download_prices,
    load_universe, make_model, validate_universe_prices,
)
from trader.predictive_edge import (
    evaluate_research_continuation_gate, is_positive_95pct_block_bootstrap_ci,
    summarize_predictive_edge,
)
from trader.universe_audit import apply_point_in_time_membership, audit_universe
from trader.research import (
    add_relative_strength_features, evaluate_simple_factor_baselines,
    make_cross_sectional_frame, merge_delivery_percentages,
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


def make_regularized_boost_model() -> Pipeline:
    """Constrained boosting comparator for the cross-sectional experiment."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("classifier", HistGradientBoostingClassifier(
            max_iter=80, learning_rate=0.04, max_leaf_nodes=7,
            min_samples_leaf=40, l2_regularization=5.0, random_state=42,
        )),
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
    nifty_sma_200 = nifty.rolling(200, min_periods=200).mean()
    result["nifty_close"] = nifty.reindex(result.index)
    result["nifty_sma_200"] = nifty_sma_200.reindex(result.index)
    result["nifty_above_200dma"] = (result["nifty_close"] > result["nifty_sma_200"])
    result["india_vix"] = vix.reindex(result.index)
    result["india_vix_low_20"] = result["india_vix"] < 20.0
    result["nifty_ret_20"] = nifty.pct_change(20).reindex(result.index)
    result["nifty_vix_change"] = vix.pct_change(1).reindex(result.index)
    result = merge_delivery_percentages(result, DATA / "raw" / "delivery.csv")
    sector_path = DATA.parent / "config" / "sector_classifications.json"
    sector_config = json.loads(sector_path.read_text(encoding="utf-8"))
    result["sector"] = result["symbol"].map(sector_config["symbols"])
    return add_relative_strength_features(result)


def run_experiment() -> dict:
    # T-0003 must never fall back to the legacy static 49-symbol universe.
    # Validate the official event ledger before any market-data download or
    # model computation; a missing interval panel is also a hard blocker.
    reference_root = DATA / "reference"
    evidence_gate = audit_membership_evidence(
        reference_root / "nifty50_transition_register.csv",
        reference_root / "nifty50_annual_coverage.csv",
        reference_root,
    )
    if not evidence_gate.get("ready", False):
        errors = evidence_gate.get("errors", [])
        detail = "; ".join(errors[:8])
        if len(errors) > 8:
            detail += f"; and {len(errors) - 8} additional evidence errors"
        raise RuntimeError(
            "T-0003 full point-in-time Nifty 50 evidence gate is BLOCKED; "
            "refusing to run on the legacy static universe. " + detail
        )

    membership_path = reference_root / "universe_membership.csv"
    if not membership_path.is_file():
        raise RuntimeError(
            "T-0003 full point-in-time membership intervals are missing "
            "(data/reference/universe_membership.csv); refusing to use config/universe.txt."
        )

    sector_path = DATA.parent / "config" / "sector_classifications.json"
    sector_config = json.loads(sector_path.read_text(encoding="utf-8"))
    universe = load_universe()
    prices = download_prices(universe, period="7y")
    # Never run a cross-sectional experiment on a silently reduced universe.
    # Missing/delisted constituents must be resolved with an explicit,
    # documented corporate-action/history treatment before research proceeds.
    validate_universe_prices(universe, prices)
    delivery_status = download_delivery_history(prices, DATA / "raw" / "delivery.csv")
    universe_audit = audit_universe(prices, universe, membership_path)
    frame = build_experiment_frame(prices)
    frame, membership_application = apply_point_in_time_membership(
        frame, membership_path, universe_audit,
    )
    corporate_action_audit = audit_corporate_action_ledger(
        DATA / "reference" / "corporate_actions.csv",
    )
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
    # Experiment A: predict which stocks beat the same-day universe median.
    # Raw market-wide variables are excluded; every retained feature is ranked
    # cross-sectionally before fitting to avoid market-timing leakage.
    cross_frame, cross_features = make_cross_sectional_frame(labelled, EXPERIMENT_FEATURES)
    cross_frame = cross_frame.dropna(subset=["target"]).copy()
    cross_metrics = walk_forward_evaluate(
        cross_frame, cross_features, make_regularized_boost_model,
        horizon=5, train_years=3, test_months=3,
        baseline_factory=make_logistic_model, shuffle_repeats=99,
        shuffle_within_date=True, collect_oos_predictions=True,
    )
    cross_oos_predictions = cross_metrics.pop("oos_predictions", [])
    predictive_edge = summarize_predictive_edge(cross_metrics)
    factor_baselines = evaluate_simple_factor_baselines(
        cross_frame, horizon=5, train_years=3, test_months=3, picks_per_day=5,
    )

    metrics["simple_factor_baselines"] = factor_baselines
    metrics["stage_2_predictive_edge"] = predictive_edge

    metrics["cross_sectional_experiment"] = {
        "description": "Within-date percentile-ranked stock features; target is net return above that date's universe median.",
        "rows": int(len(cross_frame)),
        "features": cross_features,
        "excluded_market_features": ["nifty_ret_1", "nifty_ret_5", "nifty_ret_10", "nifty_ret_20", "nifty_vix", "nifty_vix_change"],
        "boosting_model": "HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=7,min_samples_leaf=40,l2_regularization=5.0)",
        "logistic_baseline": "LogisticRegression(C=0.1)",
        "fold_metrics": cross_metrics,
    }
    # The regime gate must evaluate the same cross-sectional model picks as A.
    # Using metrics["folds"] here would silently substitute the pooled model.
    regime_fold_metrics = [
        {"test_start": row["test_start"], "test_end": row["test_end"], "regime_performance": row.get("regime_performance")}
        for row in cross_metrics.get("folds", [])
    ]
    gate_key = "nifty_above_200dma_vix_below_20"
    gate_excess = [
        item["regime_performance"][gate_key]["top5_minus_universe"]
        for item in regime_fold_metrics
        if item.get("regime_performance") and item["regime_performance"].get(gate_key)
        and item["regime_performance"][gate_key].get("top5_minus_universe") is not None
    ]
    regime_positive_folds = sum(value > 0 for value in gate_excess)
    majority_folds = (cross_metrics.get("fold_count", 0) // 2) + 1
    cross_ci = cross_metrics.get("top5_minus_universe_net_return_block_bootstrap_95pct")
    cross_pass = (
        cross_metrics.get("folds_with_positive_net_excess", 0) >= majority_folds
        and is_positive_95pct_block_bootstrap_ci(
            cross_ci, expected_method="circular_moving_block_bootstrap"
        )
    )
    regime_pass = regime_positive_folds >= majority_folds
    portfolio_diagnostics = {"status": "unavailable", "reason": "No out-of-sample candidate predictions were collected."}
    if cross_oos_predictions:
        from trader.portfolio_diagnostics import (
            index_benchmarks, random_pick_monte_carlo,
            simulate_mark_to_market_portfolio,
        )
        oos_frame = pd.DataFrame(cross_oos_predictions)
        model_picks = (
            oos_frame.sort_values(["signal_date", "score", "symbol"],
                                  ascending=[True, False, True], kind="mergesort")
            .groupby("signal_date", sort=True).head(5).copy()
        )
        daily_price_parts = [
            pd.DataFrame({"date": stock.index, "symbol": symbol, "close": stock["close"].to_numpy()})
            for symbol, stock in prices.items()
            if (not symbol.startswith("^") or symbol == "^NSEI") and "close" in stock
        ]
        daily_price_panel = pd.concat(daily_price_parts, ignore_index=True)
        portfolio_risk_kwargs = {
            "max_participation_rate": 0.01,
            "max_sector_exposure_fraction": 0.30,
            "drawdown_size_reduction_threshold": 0.10,
            "drawdown_size_multiplier": 0.50,
            "cost_parameters": DEFAULT_DELIVERY_COSTS,
        }
        model_portfolio = simulate_mark_to_market_portfolio(
            model_picks, daily_price_panel, **portfolio_risk_kwargs,
        )
        # Predeclared turnover sensitivity: compare one, two and five picks
        # without selecting the best result or changing the locked holdout.
        top_pick_sensitivity = {}
        for pick_count in (1, 2, 5):
            selected = (
                oos_frame.sort_values(
                    ["signal_date", "score", "symbol"],
                    ascending=[True, False, True], kind="mergesort",
                ).groupby("signal_date", sort=True).head(pick_count).copy()
            )
            result = simulate_mark_to_market_portfolio(
                selected, daily_price_panel, **portfolio_risk_kwargs,
            )
            top_pick_sensitivity[str(pick_count)] = {
                "picks_per_signal_date": pick_count,
                "trades": result["trades"],
                "net_return": result["net_return"],
                "max_daily_drawdown": result["max_daily_drawdown"],
                "peak_sector_exposure": result["peak_sector_exposure"],
                "average_gross_exposure": result["average_gross_exposure"],
                "rejected": result["rejected"],
                "interpretation": "predeclared turnover sensitivity; not a parameter-selection gate",
            }
        random_benchmark = random_pick_monte_carlo(
            oos_frame, daily_price_panel, simulations=300, seed=42052,
            max_participation_rate=0.01, max_sector_exposure_fraction=0.30,
            drawdown_size_reduction_threshold=0.10, drawdown_size_multiplier=0.50,
            cost_parameters=DEFAULT_DELIVERY_COSTS,
        )
        cost_stress = {}
        for slippage_bps in (2.0, 5.0, 10.0, 20.0):
            stress_costs = {**DEFAULT_DELIVERY_COSTS, "slippage_bps_per_side": slippage_bps}
            stress_result = simulate_mark_to_market_portfolio(
                model_picks, daily_price_panel, max_participation_rate=0.01,
                max_sector_exposure_fraction=0.30,
                drawdown_size_reduction_threshold=0.10,
                drawdown_size_multiplier=0.50,
                cost_parameters=stress_costs,
            )
            cost_stress[str(int(slippage_bps)) + "_bps_per_side"] = {
                "net_return": stress_result["net_return"],
                "max_daily_drawdown": stress_result["max_daily_drawdown"],
                "trades": stress_result["trades"],
                "liquidity_rejections": stress_result["rejected"]["liquidity"],
            }
        index_comparisons = index_benchmarks(
            model_portfolio["daily_equity"], daily_price_panel, index_symbol="^NSEI",
        )
        portfolio_diagnostics = {
            "daily_mark_to_market_model": model_portfolio,
            "top_pick_turnover_sensitivity": top_pick_sensitivity,
            "random_pick_monte_carlo": random_benchmark,
            "nifty_benchmarks": index_comparisons,
            "cost_stress_by_slippage_bps_per_side": cost_stress,
            "liquidity_participation_cap": 0.01,
            "max_sector_exposure_fraction": 0.30,
            "drawdown_size_reduction_threshold": 0.10,
            "drawdown_size_multiplier_after_threshold": 0.50,
            "liquidity_source": "NSE sec_bhavdata_full TURNOVER_LACS, trailing 20-session average",
            "sector_classification": {
                "path": "config/sector_classifications.json",
                "classification_as_of": sector_config["classification_as_of"],
                "source_url": sector_config["source_url"],
                "note": sector_config["note"],
            },
            "comparison_note": "Model and random portfolios use the same out-of-sample signal dates, eligible candidate pool, five-pick daily limit, cash sizing, 30% sector exposure cap, 50% sizing after a 10% drawdown, 1% of trailing 20-session NSE rupee turnover cap, price panel, and actual-notional cost calculation. Random picks are uniform without replacement per signal date.",
        }
    metrics["portfolio_diagnostics"] = portfolio_diagnostics
    metrics["regime_experiment"] = {
        "description": "Predeclared four-way regime split of the cross-sectional model top-five picks versus the same-day universe; no thresholds fitted to test outcomes.",
        "nifty_regime_rule": "Nifty close above its trailing 200-session moving average (200 observations required).",
        "vix_regime_rule": "India VIX below 20.0 versus at or above 20.0.",
        "gated_strategy": "Risk-on / lower-volatility only: Nifty above 200DMA AND India VIX below 20.",
        "risk_on_low_vol_positive_excess_folds": int(regime_positive_folds),
        "risk_on_low_vol_evaluable_folds": int(len(gate_excess)),
        "fold_metrics": regime_fold_metrics,
    }
    research_gate = evaluate_research_continuation_gate(
        cross_metrics,
        regime_positive_folds,
        predictive_edge,
        point_in_time_universe_verified=bool(
            membership_application.get("point_in_time_verified", False)
        ),
        corporate_action_adjustments_verified=bool(
            corporate_action_audit.get("corporate_action_adjustment_verified", False)
        ),
    )
    metrics["research_continuation_gate"] = research_gate
    metrics["stopping_rule"] = {
        "criterion": "Require positive relative excess in a strict majority of folds, a positive lower 95% block-bootstrap bound, positive absolute top-five net return, a passing predeclared regime check, a statistically positive AUC advantage over logistic, and verified point-in-time universe and corporate-action data.",
        "majority_folds_required": int(majority_folds),
        "cross_sectional_A_pass": bool(cross_pass),
        "regime_gate_B_pass": bool(regime_pass),
        "continue_price_feature_tuning": bool(
            research_gate["continue_price_feature_research_only"]
        ),
        "decision": research_gate["decision"],
        "cross_sectional_top5_mean_net_return": cross_metrics.get("mean_top5_net_return"),
        "cross_sectional_absolute_profitability_pass": bool(
            cross_metrics.get("mean_top5_net_return") is not None
            and cross_metrics["mean_top5_net_return"] > 0
        ),
        "promotion_eligible": False,
        "note": "All returns are after the configured transaction-cost model. Relative ranking alone is insufficient. No final-holdout access, promotion or live execution is authorised by this exploratory gate.",
    }
    metrics["reporting_diagnostics"] = {
        "fold_auc_above_0_5": metrics.get("folds_auc_above_0_5"),
        "fold_auc_count": metrics.get("fold_count"),
        "top5_minus_universe_net_return_block_bootstrap_95pct": metrics.get("top5_minus_universe_net_return_block_bootstrap_95pct"),
        "bootstrap_note": "Circular 5-trading-day moving-block bootstrap of daily top-five minus universe net-return spread; preserves short-horizon dependence from overlapping labels.",
    }
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
    metrics["universe_integrity_audit"] = universe_audit
    metrics["membership_application"] = membership_application
    metrics["corporate_action_audit"] = corporate_action_audit
    metrics["final_holdout_protocol"] = {
        "path": "config/final_holdout_protocol.json",
        "status": "LOCKED_NOT_EVALUATED",
        "holdout_metrics_computed": False,
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
    metrics["broker_cost_profile"] = "Groww NSE equity delivery (config/broker_costs_groww.json)"
    metrics["cost_note"] = (
        "Groww published NSE equity-delivery brokerage and DP schedule checked 2026-11-05; "
        "2 bps slippage per side remains a configurable scenario assumption, not an observed fill. "
        "The standard ₹20 pre-GST DP charge is used by default; account-specific DP concessions "
        "can be configured. Reconcile against contract notes before live use."
    )

    # Freeze the exact OHLCV and delivery inputs used by this experiment.
    raw_dir = DATA / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    price_parts = []
    for symbol, stock in prices.items():
        available = [column for column in ("open", "high", "low", "close", "volume")
                     if column in stock.columns]
        if available:
            part = stock[available].copy()
            part["date"] = part.index
            part["symbol"] = symbol
            price_parts.append(part.reset_index(drop=True))
    price_panel_path = raw_dir / "price_panel.csv"
    pd.concat(price_parts, ignore_index=True).sort_values(["date", "symbol"]).to_csv(
        price_panel_path, index=False
    )
    snapshot_inputs = [price_panel_path]
    reference_ledgers = (
        DATA / "reference" / "universe_membership.csv",
        DATA / "reference" / "corporate_actions.csv",
    )
    for candidate in (
        raw_dir / "delivery.csv",
        raw_dir / "delivery_download_log.csv",
        *reference_ledgers,
        DATA.parent / "config" / "universe.txt",
        DATA.parent / "config" / "broker_costs_groww.json",
        DATA.parent / "config" / "sector_classifications.json",
        DATA.parent / "config" / "final_holdout_protocol.json",
    ):
        if candidate.is_file():
            snapshot_inputs.append(candidate)

    # Freeze every evidence file referenced by a membership or corporate-action
    # ledger, not just the ledger row containing its checksum.
    for ledger_path in reference_ledgers:
        if not ledger_path.is_file():
            continue
        ledger = pd.read_csv(ledger_path)
        if "evidence_path" not in ledger.columns:
            continue
        for evidence_value in ledger["evidence_path"].dropna().astype(str):
            evidence_path = Path(evidence_value)
            if not evidence_path.is_absolute():
                evidence_path = ledger_path.parent / evidence_path
            if evidence_path.is_file():
                snapshot_inputs.append(evidence_path)

    snapshot_manifest = write_data_snapshot_manifest(
        snapshot_inputs,
        DATA / "snapshots" / "input_manifest.json",
        root=DATA.parent,
        metadata={
            "git_commit": os.environ.get("GITHUB_SHA", "local-unpinned"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "universe_policy": "owner-confirmed fixed 49-symbol custom universe; no silent additions or substitutions",
            "portfolio_risk_limits": {
                "max_sector_exposure_fraction": 0.30,
                "drawdown_size_reduction_threshold": 0.10,
                "drawdown_size_multiplier": 0.50,
                "max_participation_rate": 0.01,
            },
            "experiment": "triple_barrier_relative_strength_delivery",
            "price_source": "Yahoo Finance via yfinance; independently verify adjusted-price lineage",
            "delivery_source": "NSE full bhavcopy sec_bhavdata_full",
        },
    )
    metrics["data_snapshot_manifest"] = snapshot_manifest

    report_dir = DATA / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "triple_barrier_experiment.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    return metrics


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2))
