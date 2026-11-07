from __future__ import annotations

import math

import numpy as np
import pandas as pd

from trader.costs import DEFAULT_DELIVERY_COSTS, delivery_round_trip_cost


PILOT_MAX_PARTICIPATION = 0.02
PILOT_REFERENCE_PARTICIPATION = 0.01
PILOT_MIN_MEDIAN_TURNOVER_RUPEES = 50_000_000.0
PILOT_LIQUIDITY_LOOKBACK_SESSIONS = 20


def _nse_session_dates(values: pd.Series) -> pd.Series:
    """Normalize naive NSE dates as local dates and aware timestamps to Asia/Kolkata."""
    def as_date(value):
        try:
            stamp = pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError):
            return pd.NaT
        if pd.isna(stamp):
            return pd.NaT
        if stamp.tzinfo is not None:
            stamp = stamp.tz_convert("Asia/Kolkata").tz_localize(None)
        return stamp.normalize()

    return pd.Series(values.map(as_date), index=values.index, dtype="datetime64[ns]")


def _nse_cutoff(value: str | pd.Timestamp) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("as_of must be a valid NSE calendar date")
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("Asia/Kolkata").tz_localize(None)
    return stamp.normalize()


def pilot_slippage_bps(participation_fraction: float, *, stress_multiplier: float = 1.0) -> float:
    """Registered per-side scenario, not a fill guarantee."""
    if not np.isfinite(participation_fraction) or not 0 < participation_fraction <= PILOT_MAX_PARTICIPATION:
        raise ValueError("participation_fraction must be finite and in (0, 2%]")
    if not np.isfinite(stress_multiplier) or stress_multiplier <= 0:
        raise ValueError("stress_multiplier must be finite and positive")
    return float((15.0 + 25.0 * math.sqrt(participation_fraction / 0.01)) * stress_multiplier)


def pilot_delivery_round_trip_cost(
    entry_price: float,
    exit_price: float,
    *,
    notional_rupees: float,
    participation_fraction: float,
    stress_multiplier: float = 1.0,
    cost_parameters: dict | None = None,
) -> dict:
    """Combine the registered pilot slippage scenario with the delivery fee engine.

    The participation fraction is an explicit input for the modeled order; it
    is not inferred from a price series. The result remains a scenario estimate,
    not an observed fill or empirical slippage calibration.
    """
    if not np.isfinite(notional_rupees) or notional_rupees <= 0:
        raise ValueError("notional_rupees must be finite and positive")
    slippage = pilot_slippage_bps(
        participation_fraction, stress_multiplier=stress_multiplier
    )
    parameters = dict(
        DEFAULT_DELIVERY_COSTS if cost_parameters is None else cost_parameters
    )
    parameters["notional_rupees"] = float(notional_rupees)
    parameters["slippage_bps_per_side"] = slippage
    estimate = delivery_round_trip_cost(entry_price, exit_price, **parameters)
    return {
        **estimate,
        "participation_fraction": float(participation_fraction),
        "stress_multiplier": float(stress_multiplier),
        "slippage_bps_per_side": slippage,
        "slippage_basis": "registered_pilot_scenario_not_observed_execution",
    }


def assess_pilot_liquidity(
    history: pd.DataFrame, *, as_of: str | pd.Timestamp,
    minimum_median_turnover_rupees: float = PILOT_MIN_MEDIAN_TURNOVER_RUPEES,
    lookback_sessions: int = PILOT_LIQUIDITY_LOOKBACK_SESSIONS,
) -> dict:
    """Fail-closed 20-session median traded-value screen, excluding future rows.

    Required columns: date, traded_value_rupees. Session dates are interpreted
    in Asia/Kolkata. The latest 20 unique observations on or before as_of are
    used; incomplete history is unresolved.
    """
    required = {"date", "traded_value_rupees"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(f"Liquidity history missing columns: {sorted(missing)}")
    if lookback_sessions != PILOT_LIQUIDITY_LOOKBACK_SESSIONS:
        raise ValueError("Nifty 50 pilot liquidity lookback is fixed at 20 sessions")
    if not np.isfinite(minimum_median_turnover_rupees) or minimum_median_turnover_rupees <= 0:
        raise ValueError("minimum median turnover must be finite and positive")

    data = history.loc[:, ["date", "traded_value_rupees"]].copy()
    data["date"] = _nse_session_dates(data["date"])
    data["traded_value_rupees"] = pd.to_numeric(data["traded_value_rupees"], errors="coerce")
    cutoff = _nse_cutoff(as_of)
    data = data.loc[data["date"].notna() & (data["date"] <= cutoff)]
    if data["date"].duplicated().any():
        raise ValueError("Liquidity history contains duplicate trading sessions")
    data = data.sort_values("date").tail(lookback_sessions)
    valid_values = (
        data["traded_value_rupees"].notna()
        & np.isfinite(data["traded_value_rupees"])
        & (data["traded_value_rupees"] > 0)
    )
    if len(data) != lookback_sessions or not bool(valid_values.all()):
        return {
            "status": "UNRESOLVED_INSUFFICIENT_HISTORY", "eligible": False,
            "observations": int(valid_values.sum()), "required_observations": lookback_sessions,
            "median_turnover_rupees": None, "as_of": cutoff.date().isoformat(),
        }
    median = float(data["traded_value_rupees"].median())
    return {
        "status": "PASS" if median >= minimum_median_turnover_rupees else "FAIL_LIQUIDITY",
        "eligible": bool(median >= minimum_median_turnover_rupees),
        "observations": lookback_sessions, "required_observations": lookback_sessions,
        "median_turnover_rupees": median,
        "minimum_turnover_rupees": float(minimum_median_turnover_rupees),
        "as_of": cutoff.date().isoformat(),
        "window_start": data["date"].iloc[0].date().isoformat(),
        "window_end": data["date"].iloc[-1].date().isoformat(),
    }


def cap_pilot_fill(
    requested_quantity: int, *, price_rupees: float, traded_value_rupees: float,
    max_participation_fraction: float = PILOT_MAX_PARTICIPATION,
) -> dict:
    """Cap quantity at the traded-value participation limit and expose remainder.

    This is a deterministic research guard, not an intraday execution simulator.
    """
    if isinstance(requested_quantity, bool) or not isinstance(requested_quantity, (int, np.integer)) or requested_quantity < 0:
        raise ValueError("requested_quantity must be a non-negative integer")
    for name, value in (("price_rupees", price_rupees), ("traded_value_rupees", traded_value_rupees)):
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if not np.isfinite(max_participation_fraction) or not 0 < max_participation_fraction <= PILOT_MAX_PARTICIPATION:
        raise ValueError("max_participation_fraction must be in (0, 2%]")
    max_notional = float(traded_value_rupees) * float(max_participation_fraction)
    max_quantity = int(math.floor(max_notional / float(price_rupees)))
    filled = min(int(requested_quantity), max_quantity)
    return {
        "requested_quantity": int(requested_quantity), "filled_quantity": filled,
        "unfilled_quantity": int(requested_quantity) - filled,
        "executed_notional_rupees": float(filled * price_rupees),
        "max_participation_fraction": float(max_participation_fraction),
        "actual_participation_fraction": float(filled * price_rupees / traded_value_rupees),
        "status": "FILLED" if filled == requested_quantity else ("PARTIAL" if filled else "UNFILLED"),
    }
