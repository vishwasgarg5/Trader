"""Fail-closed point-in-time, power, validation and evidence controls for NIFTY50_PILOT_001.

These helpers are engineering contracts. They do not fetch market data, certify sources,
open the final holdout, or authorize model evaluation or trading.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

import numpy as np
import pandas as pd

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FEATURE_COLUMNS = {
    "security_id", "feature_name", "value", "published_at", "first_seen_at",
    "source_url", "source_sha256",
}


def _utc_series(values: pd.Series, field: str) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce", utc=True)
    if parsed.isna().any():
        raise ValueError(f"{field} contains missing or invalid timestamps")
    return parsed


def validate_point_in_time_features(features: pd.DataFrame) -> pd.DataFrame:
    """Validate provenance and calculate the earliest defensible availability time.

    A datum is available only after both its publication time and the system's
    first-seen time. Revised/backfilled records therefore cannot be backdated.
    """
    missing = REQUIRED_FEATURE_COLUMNS.difference(features.columns)
    if missing:
        raise ValueError(f"Feature table missing columns: {sorted(missing)}")
    result = features.copy()
    for field in ("security_id", "feature_name", "source_url", "source_sha256"):
        result[field] = result[field].astype("string").str.strip()
        if result[field].isna().any() or result[field].eq("").any():
            raise ValueError(f"{field} contains blank values")
    if result["security_id"].str.upper().ne(result["security_id"]).any():
        raise ValueError("security_id must use canonical uppercase identifiers")
    if result["source_sha256"].map(lambda x: not bool(SHA256_RE.fullmatch(str(x)))).any():
        raise ValueError("source_sha256 must contain lowercase 64-character SHA-256 digests")
    for value in result["source_url"]:
        parsed = urlparse(str(value))
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("source_url must be an absolute HTTPS URL")
    result["published_at"] = _utc_series(result["published_at"], "published_at")
    result["first_seen_at"] = _utc_series(result["first_seen_at"], "first_seen_at")
    result["available_at"] = result[["published_at", "first_seen_at"]].max(axis=1)
    if result["value"].isna().any():
        raise ValueError("feature value cannot be missing")
    key = ["security_id", "feature_name", "available_at", "source_sha256"]
    if result.duplicated(key).any():
        raise ValueError("duplicate feature provenance rows")
    return result.sort_values(
        ["security_id", "feature_name", "available_at"], kind="mergesort"
    ).reset_index(drop=True)


def build_point_in_time_feature_snapshot(
    features: pd.DataFrame, signals: pd.DataFrame
) -> pd.DataFrame:
    """Select the latest known value for each security/feature at each signal time."""
    required_signals = {"signal_id", "security_id", "signal_timestamp"}
    missing = required_signals.difference(signals.columns)
    if missing:
        raise ValueError(f"Signal table missing columns: {sorted(missing)}")
    checked = validate_point_in_time_features(features)
    requests = signals.copy()
    requests["security_id"] = requests["security_id"].astype("string").str.strip()
    requests["signal_timestamp"] = _utc_series(
        requests["signal_timestamp"], "signal_timestamp"
    )
    if requests["signal_id"].isna().any() or requests["signal_id"].astype(str).str.strip().eq("").any():
        raise ValueError("signal_id must be present")
    if requests.duplicated(["signal_id", "security_id"]).any():
        raise ValueError("duplicate signal_id/security_id rows")
    rows: list[dict] = []
    for signal in requests.to_dict(orient="records"):
        eligible = checked.loc[
            (checked["security_id"] == signal["security_id"])
            & (checked["available_at"] <= signal["signal_timestamp"])
        ]
        if eligible.empty:
            continue
        latest = eligible.sort_values("available_at", kind="mergesort").groupby(
            "feature_name", sort=True, as_index=False
        ).tail(1)
        for feature in latest.to_dict(orient="records"):
            rows.append({
                "signal_id": signal["signal_id"],
                "security_id": signal["security_id"],
                "signal_timestamp": signal["signal_timestamp"],
                "feature_name": feature["feature_name"],
                "value": feature["value"],
                "available_at": feature["available_at"],
                "source_url": feature["source_url"],
                "source_sha256": feature["source_sha256"],
            })
    return pd.DataFrame(rows, columns=[
        "signal_id", "security_id", "signal_timestamp", "feature_name",
        "value", "available_at", "source_url", "source_sha256",
    ])


def _moving_block_means(
    values: np.ndarray, *, block_sessions: int, simulations: int, rng: np.random.Generator
) -> np.ndarray:
    n = len(values)
    if block_sessions < 1 or block_sessions > n:
        raise ValueError("block_sessions must be between 1 and the number of dates")
    blocks_needed = math.ceil(n / block_sessions)
    starts = rng.integers(0, n - block_sessions + 1, size=(simulations, blocks_needed))
    sampled = np.empty((simulations, blocks_needed * block_sessions), dtype=float)
    offsets = np.arange(block_sessions)
    for j in range(blocks_needed):
        sampled[:, j * block_sessions:(j + 1) * block_sessions] = values[
            starts[:, j, None] + offsets[None, :]
        ]
    return sampled[:, :n].mean(axis=1)


def estimate_precision_lift_mde(
    daily_counts: pd.DataFrame,
    *,
    alpha: float,
    target_power: float,
    seed: int,
    simulations: int = 20_000,
    block_sessions: int = 20,
    mde_ceiling: float = 0.06,
) -> dict:
    """Estimate one-sided precision-lift MDE using a moving time-block bootstrap.

    daily_counts must contain one row per qualifying date and the actual number
    of selected positives/selected names and eligible positives/eligible names.
    Exactly five names and at least 30 eligible securities are required per date.
    All design choices are explicit arguments: the protocol still requires them
    to be preregistered before this routine is used on real observations.
    """
    required = {
        "date", "selected_positive_count", "selected_count",
        "eligible_positive_count", "eligible_count",
    }
    missing = required.difference(daily_counts.columns)
    if missing:
        raise ValueError(f"Power input missing columns: {sorted(missing)}")
    if not (0 < alpha < 0.5 and 0.5 < target_power < 1):
        raise ValueError("alpha and target_power must be explicitly valid probabilities")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if simulations < 1 or not 0 < mde_ceiling <= 1:
        raise ValueError("simulations and mde_ceiling must be positive")
    data = daily_counts.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    if data["date"].isna().any() or data["date"].duplicated().any():
        raise ValueError("power input dates must be valid and unique")
    count_cols = [
        "selected_positive_count", "selected_count",
        "eligible_positive_count", "eligible_count",
    ]
    for column in count_cols:
        numeric = pd.to_numeric(data[column], errors="coerce")
        if numeric.isna().any() or not np.isfinite(numeric).all() or (numeric % 1 != 0).any():
            raise ValueError(f"{column} must contain finite integer counts")
        data[column] = numeric.astype(int)
    valid = (
        data["selected_count"].eq(5)
        & data["eligible_count"].ge(30)
        & data["selected_positive_count"].between(0, 5)
        & data["eligible_positive_count"].between(0, data["eligible_count"])
    )
    if not bool(valid.all()):
        raise ValueError("each qualifying date requires exactly five picks, >=30 eligible names and valid counts")
    data = data.sort_values("date", kind="mergesort")
    if len(data) < block_sessions:
        return {
            "status": "INSUFFICIENT_QUALIFYING_DATES",
            "qualifying_dates": len(data),
            "required_dates_for_block_bootstrap": block_sessions,
            "mde": None,
            "decision": "INCONCLUSIVE",
            "promotion_eligible": False,
        }
    selected_precision = data["selected_positive_count"].to_numpy() / 5.0
    eligible_base_rate = (
        data["eligible_positive_count"].to_numpy()
        / data["eligible_count"].to_numpy()
    )
    daily_lift = selected_precision - eligible_base_rate
    rng = np.random.default_rng(int(seed))
    null_means = _moving_block_means(
        daily_lift - daily_lift.mean(), block_sessions=block_sessions,
        simulations=simulations, rng=rng,
    )
    critical_value = float(np.quantile(null_means, 1.0 - alpha))
    grid = np.linspace(0.0, 0.50, 1001)
    power = np.array([(null_means + effect > critical_value).mean() for effect in grid])
    reached = np.flatnonzero(power >= target_power)
    mde = float(grid[reached[0]]) if len(reached) else None
    decision = (
        "INCONCLUSIVE" if mde is None or mde > mde_ceiling else "MDE_WITHIN_REGISTERED_CEILING"
    )
    return {
        "status": "ESTIMATED_SYNTHETIC_OR_EMPIRICAL_INPUT_REQUIRED",
        "qualifying_dates": int(len(data)),
        "mean_observed_precision_lift": float(daily_lift.mean()),
        "alpha_one_sided": float(alpha),
        "target_power": float(target_power),
        "seed": int(seed),
        "simulations": int(simulations),
        "block_sessions": int(block_sessions),
        "mde": mde,
        "mde_ceiling": float(mde_ceiling),
        "decision": decision,
        "method": "centered_moving_time_block_bootstrap_one_sided",
        "preserves_time_dependence": True,
        "preserves_cross_sectional_daily_aggregation": True,
        "promotion_eligible": False,
        "note": "Power/MDE is feasibility only, not evidence of predictive edge.",
    }


@dataclass(frozen=True)
class WalkForwardFold:
    fold: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    test_start: str
    test_end: str
    purge_sessions: int


def build_purged_walk_forward_folds(
    observations: pd.DataFrame,
    development_sessions: Iterable,
    *,
    min_train_sessions: int,
    test_window_sessions: int,
    purge_sessions: int = 6,
) -> list[WalkForwardFold]:
    """Build expanding chronological folds using actual outcome end dates.

    Only development_sessions may be supplied; the function has no holdout input.
    A training label must end strictly before the six-session purge boundary.
    """
    required = {"signal_date", "outcome_end_date"}
    missing = required.difference(observations.columns)
    if missing:
        raise ValueError(f"walk-forward observations missing columns: {sorted(missing)}")
    sessions = pd.DatetimeIndex(pd.to_datetime(list(development_sessions), errors="coerce")).normalize()
    if sessions.isna().any() or sessions.has_duplicates or not sessions.is_monotonic_increasing:
        raise ValueError("development_sessions must be valid, unique and chronologically sorted")
    if min_train_sessions < 1 or test_window_sessions < 1 or purge_sessions < 1:
        raise ValueError("train, test and purge session counts must be positive")
    data = observations.copy().reset_index(drop=True)
    for column in ("signal_date", "outcome_end_date"):
        data[column] = pd.to_datetime(data[column], errors="coerce").dt.normalize()
        if data[column].isna().any():
            raise ValueError(f"{column} contains invalid dates")
        if not data[column].isin(sessions).all():
            raise ValueError(f"{column} contains dates outside the supplied development calendar")
    session_index = {date: i for i, date in enumerate(sessions)}
    signal_idx = data["signal_date"].map(session_index).to_numpy(dtype=int)
    outcome_idx = data["outcome_end_date"].map(session_index).to_numpy(dtype=int)
    if (outcome_idx < signal_idx).any():
        raise ValueError("outcome_end_date cannot precede signal_date")
    folds: list[WalkForwardFold] = []
    test_start_idx = min_train_sessions + purge_sessions
    fold_number = 0
    while test_start_idx < len(sessions):
        test_end_idx = min(test_start_idx + test_window_sessions, len(sessions))
        # Six complete sessions immediately before the test window are purged.
        purge_boundary_idx = test_start_idx - purge_sessions
        train_mask = (signal_idx < test_start_idx) & (outcome_idx < purge_boundary_idx)
        test_mask = (signal_idx >= test_start_idx) & (signal_idx < test_end_idx)
        train_indices = tuple(np.flatnonzero(train_mask).tolist())
        test_indices = tuple(np.flatnonzero(test_mask).tolist())
        if train_indices and test_indices:
            fold_number += 1
            folds.append(WalkForwardFold(
                fold=fold_number,
                train_indices=train_indices,
                test_indices=test_indices,
                test_start=sessions[test_start_idx].date().isoformat(),
                test_end=sessions[test_end_idx - 1].date().isoformat(),
                purge_sessions=purge_sessions,
            ))
        test_start_idx = test_end_idx
    return folds


def evaluate_factor_alpha_gate(
    *, alpha_lower_95: float | None,
    factor_definitions_frozen: bool,
    inference_sensitivity_frozen: bool,
    data_validated: bool,
    human_reviewed: bool,
) -> dict:
    """Fail-closed factor-alpha gate; point estimate alone is never sufficient."""
    valid_number = (
        alpha_lower_95 is not None
        and math.isfinite(float(alpha_lower_95))
    )
    passed = (
        valid_number and float(alpha_lower_95) > 0
        and factor_definitions_frozen is True
        and inference_sensitivity_frozen is True
        and data_validated is True
        and human_reviewed is True
    )
    blockers = []
    if not valid_number or float(alpha_lower_95) <= 0:
        blockers.append("95_percent_lower_confidence_bound_not_above_zero")
    if factor_definitions_frozen is not True:
        blockers.append("factor_definitions_not_frozen")
    if inference_sensitivity_frozen is not True:
        blockers.append("inference_sensitivity_not_frozen")
    if data_validated is not True:
        blockers.append("data_not_validated")
    if human_reviewed is not True:
        blockers.append("independent_human_review_missing")
    return {
        "passed": bool(passed),
        "alpha_lower_95": float(alpha_lower_95) if valid_number else None,
        "blockers": blockers,
        "promotion_eligible": False,
    }


def evaluate_all_pilot_gates(
    gate_results: dict[int, bool],
    *,
    upstream_data_validated: bool,
    independent_human_reviewed: bool,
    protocol_frozen: bool,
) -> dict:
    """Require all 16 registered gates and evidence states; never authorize deployment."""
    expected = set(range(1, 17))
    supplied = set(gate_results)
    missing = sorted(expected - supplied)
    failed = sorted(gate for gate in expected if gate in gate_results and gate_results[gate] is not True)
    blockers = []
    if missing:
        blockers.append("missing_gate_results:" + ",".join(map(str, missing)))
    if failed:
        blockers.append("failed_or_non_boolean_gates:" + ",".join(map(str, failed)))
    if upstream_data_validated is not True:
        blockers.append("upstream_data_not_validated")
    if independent_human_reviewed is not True:
        blockers.append("independent_human_review_missing")
    if protocol_frozen is not True:
        blockers.append("protocol_not_frozen")
    eligible = not blockers
    return {
        "status": "ELIGIBLE_FOR_SEPARATELY_APPROVED_BROADER_EXPERIMENT" if eligible else "RESEARCH_HOLD",
        "blockers": blockers,
        "all_registered_gates_passed": eligible,
        "pilot_go_authorizes_promotion": False,
        "pilot_go_authorizes_paper_trading": False,
        "pilot_go_authorizes_live_trading": False,
        "promotion_eligible": False,
        "live_execution_enabled": False,
    }


def sha256_bytes(content: bytes) -> str:
    """Return the SHA-256 digest of original source bytes."""
    return hashlib.sha256(content).hexdigest()


def validate_source_manifest(records: pd.DataFrame) -> pd.DataFrame:
    """Validate immutable source provenance rows; does not attest source authenticity."""
    required = {"source_id", "source_url", "source_sha256", "retrieved_at"}
    missing = required.difference(records.columns)
    if missing:
        raise ValueError(f"source manifest missing columns: {sorted(missing)}")
    result = records.copy()
    for field in ("source_id", "source_url", "source_sha256"):
        result[field] = result[field].astype("string").str.strip()
        if result[field].isna().any() or result[field].eq("").any():
            raise ValueError(f"{field} contains blank values")
    if result["source_id"].duplicated().any():
        raise ValueError("source_id values must be unique")
    if result["source_sha256"].map(lambda x: not bool(SHA256_RE.fullmatch(str(x)))).any():
        raise ValueError("source_sha256 must be lowercase 64-character SHA-256 hex")
    if result["source_url"].map(lambda x: urlparse(str(x)).scheme != "https" or not urlparse(str(x)).netloc).any():
        raise ValueError("source_url must be HTTPS")
    result["retrieved_at"] = _utc_series(result["retrieved_at"], "retrieved_at")
    return result
