"""Fail-closed fixed-horizon labels for the Nifty 50 pilot.

This module computes labels only from already-derived, reviewed interval returns.
It does not fetch data, infer membership, estimate costs, or authorize evaluation.
"""
from __future__ import annotations

import math

import pandas as pd


PILOT_HOLDING_SESSIONS = 5
PILOT_POSITIVE_EXCESS_THRESHOLD = 0.01
REQUIRED_COLUMNS = {
    "security_id",
    "signal_date",
    "entry_date",
    "exit_date",
    "entry_session_ordinal",
    "exit_session_ordinal",
    "stock_total_return",
    "benchmark_tri_return",
    "reference_cost_fraction",
}


def build_fixed_horizon_labels(
    observations: pd.DataFrame,
    *,
    membership_verified: bool,
    security_identity_verified: bool,
    stock_total_returns_verified: bool,
    benchmark_tri_verified: bool,
    execution_costs_verified: bool,
) -> pd.DataFrame:
    """Build five-session Nifty 50 TRI-relative labels from reviewed returns.

    Returns are decimal simple returns over the identical entry-to-exit interval.
    The reference cost fraction is a round-trip cost as a fraction of entry
    notional. Net stock return compounds the gross total return with that cost:
    (1 + gross stock total return) * (1 - cost fraction) - 1.

    A positive label requires net stock return minus matched Nifty 50 TRI return
    to be strictly greater than 1 percentage point. Equality is negative.
    Any unresolved prerequisite or invalid row remains UNRESOLVED, never 0.
    """
    required_flags = {
        "membership_verified": membership_verified,
        "security_identity_verified": security_identity_verified,
        "stock_total_returns_verified": stock_total_returns_verified,
        "benchmark_tri_verified": benchmark_tri_verified,
        "execution_costs_verified": execution_costs_verified,
    }
    missing_flags = [name for name, value in required_flags.items() if value is not True]
    if missing_flags:
        return _unresolved_frame(
            observations,
            f"prerequisites_not_verified:{','.join(missing_flags)}",
        )

    missing = REQUIRED_COLUMNS.difference(observations.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = observations.copy()
    for field in ("signal_date", "entry_date", "exit_date"):
        data[field] = pd.to_datetime(data[field], errors="coerce").dt.normalize()

    if data["security_id"].isna().any() or data["security_id"].astype(str).str.strip().eq("").any():
        raise ValueError("security_id must be present")
    if data.duplicated(["security_id", "signal_date"]).any():
        raise ValueError("Duplicate security_id/signal_date observations")

    results: list[dict] = []
    for row in data.to_dict(orient="records"):
        reason = None
        signal, entry, exit_ = row["signal_date"], row["entry_date"], row["exit_date"]
        if pd.isna(signal) or pd.isna(entry) or pd.isna(exit_):
            reason = "invalid_interval_date"
        elif not signal < entry < exit_:
            reason = "interval_dates_not_strictly_increasing"
        else:
            try:
                entry_raw = float(row["entry_session_ordinal"])
                exit_raw = float(row["exit_session_ordinal"])
                valid_ordinals = (
                    math.isfinite(entry_raw) and math.isfinite(exit_raw)
                    and entry_raw.is_integer() and exit_raw.is_integer()
                )
                entry_ordinal = int(entry_raw) if valid_ordinals else -1
                exit_ordinal = int(exit_raw) if valid_ordinals else -1
            except (TypeError, ValueError, OverflowError):
                entry_ordinal = exit_ordinal = -1
            if entry_ordinal < 0 or exit_ordinal - entry_ordinal != PILOT_HOLDING_SESSIONS - 1:
                reason = "interval_not_exactly_five_entry_sessions"

        values: dict[str, float] = {}
        for field in ("stock_total_return", "benchmark_tri_return", "reference_cost_fraction"):
            try:
                value = float(row[field])
            except (TypeError, ValueError, KeyError):
                value = math.nan
            values[field] = value
        if reason is None and not all(math.isfinite(v) for v in values.values()):
            reason = "non_finite_or_missing_return_input"
        if reason is None and values["stock_total_return"] <= -1:
            reason = "stock_total_return_at_or_below_minus_100_percent"
        if reason is None and values["benchmark_tri_return"] <= -1:
            reason = "benchmark_tri_return_at_or_below_minus_100_percent"
        if reason is None and not 0 <= values["reference_cost_fraction"] < 1:
            reason = "invalid_reference_cost_fraction"

        result = {
            "security_id": str(row["security_id"]),
            "signal_date": signal,
            "entry_date": entry,
            "exit_date": exit_,
            "holding_sessions": PILOT_HOLDING_SESSIONS,
            "gross_stock_total_return": values["stock_total_return"],
            "benchmark_tri_return": values["benchmark_tri_return"],
            "reference_cost_fraction": values["reference_cost_fraction"],
            "net_stock_return": math.nan,
            "net_relative_excess_return": math.nan,
            "label": pd.NA,
            "status": "UNRESOLVED" if reason else "RESOLVED",
            "reason": reason or "",
        }
        if reason is None:
            net_stock = (
                (1.0 + values["stock_total_return"])
                * (1.0 - values["reference_cost_fraction"])
                - 1.0
            )
            relative = net_stock - values["benchmark_tri_return"]
            result.update({
                "net_stock_return": net_stock,
                "net_relative_excess_return": relative,
                "label": int(
                    relative > PILOT_POSITIVE_EXCESS_THRESHOLD
                    and not math.isclose(
                        relative, PILOT_POSITIVE_EXCESS_THRESHOLD,
                        rel_tol=0.0, abs_tol=1e-12,
                    )
                ),
            })
        results.append(result)

    return pd.DataFrame(results)


def _unresolved_frame(observations: pd.DataFrame, reason: str) -> pd.DataFrame:
    """Return one unresolved record per input row without inspecting outcomes."""
    rows = []
    for row in observations.to_dict(orient="records"):
        rows.append({
            "security_id": row.get("security_id"),
            "signal_date": row.get("signal_date"),
            "entry_date": row.get("entry_date"),
            "exit_date": row.get("exit_date"),
            "holding_sessions": PILOT_HOLDING_SESSIONS,
            "gross_stock_total_return": math.nan,
            "benchmark_tri_return": math.nan,
            "reference_cost_fraction": math.nan,
            "net_stock_return": math.nan,
            "net_relative_excess_return": math.nan,
            "label": pd.NA,
            "status": "UNRESOLVED",
            "reason": reason,
        })
    return pd.DataFrame(rows)
