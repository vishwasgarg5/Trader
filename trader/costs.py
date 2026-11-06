from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# NSE cash-market exchange transaction charge (0.00297%) and IPFT (0.0001%)
# are modelled separately. Groww's published equity-delivery tariff
# checked 2026-11-05: brokerage min(₹20, 0.1% of order value), minimum
# lower of ₹5 or 2.5% of order value; delivery sell DP ₹20 (₹16.50 Groww
# + ₹3.50 depository) unless sell value is below ₹100. GST applies to
# brokerage, exchange/IPFT/SEBI and DP charges. Slippage remains a scenario input.
def load_groww_delivery_costs(config_path: str | Path | None = None) -> dict:
    """Load the single source of truth for Groww NSE equity-delivery costs."""
    path = (
        Path(config_path) if config_path is not None
        else Path(__file__).resolve().parent.parent / "config" / "broker_costs_groww.json"
    )
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to load Groww cost profile: {path}") from exc
    if profile.get("broker") != "Groww" or profile.get("segment") != "NSE equity delivery":
        raise ValueError("Cost profile must describe Groww NSE equity delivery")
    brokerage = profile["brokerage"]
    statutory = profile["statutory_and_exchange"]
    dp = profile["dp"]
    dp_total = float(dp["groww_component"]) + float(dp["depository_component_standard"])
    if not np.isclose(dp_total, float(dp["standard_pre_gst_total"]), atol=0.005):
        raise ValueError("Groww DP components do not match standard_pre_gst_total")
    costs = {
        "stt_rate_each_side": float(statutory["stt_each_side"]),
        "stamp_duty_buy_rate": float(statutory["stamp_duty_buy_side"]),
        "exchange_rate_each_side": float(statutory["nse_transaction_charge"]),
        "ipft_rate_each_side": float(statutory["nse_ipft_charge"]),
        "sebi_rate_each_side": float(statutory["sebi_turnover_charge_each_side"]),
        "gst_rate": float(statutory["gst"]),
        "brokerage_rate_each_side": float(brokerage["rate_per_executed_order"]),
        "brokerage_cap_per_order": float(brokerage["cap_per_executed_order"]),
        "brokerage_min_per_order": float(brokerage["minimum_per_executed_order"]),
        "brokerage_min_rate": float(brokerage["minimum_rate_cap"]),
        "dp_charge_per_sell": dp_total,
        "dp_groww_component_per_sell": float(dp["groww_component"]),
        "dp_depository_component_per_sell": float(dp["depository_component_standard"]),
        "dp_free_below_sell_value": float(dp["free_below_sell_value"]),
        "slippage_bps_per_side": float(profile["slippage_bps_per_side"]),
        "notional_rupees": 100000.0,
    }
    if any(not np.isfinite(value) or value < 0 for value in costs.values()):
        raise ValueError("Groww cost profile contains non-finite or negative values")
    return costs


DEFAULT_DELIVERY_COSTS = load_groww_delivery_costs()


def _groww_brokerage(turnover: float, rate: float, cap: float,
                    minimum: float, minimum_rate: float) -> float:
    """Apply Groww's per-executed-order cap and low-value minimum rule."""
    calculated = min(turnover * rate, cap)
    minimum_charge = min(minimum, turnover * minimum_rate)
    return max(calculated, minimum_charge)


def delivery_round_trip_cost(
    entry_price: float,
    exit_price: float,
    *,
    stt_rate_each_side: float = 0.001,
    stamp_duty_buy_rate: float = 0.00015,
    exchange_rate_each_side: float = 0.0000297,
    ipft_rate_each_side: float = 0.000001,
    sebi_rate_each_side: float = 0.000001,
    gst_rate: float = 0.18,
    brokerage_rate_each_side: float = 0.001,
    brokerage_cap_per_order: float = 20.0,
    brokerage_min_per_order: float = 5.0,
    brokerage_min_rate: float = 0.025,
    dp_charge_per_sell: float = 20.0,
    dp_free_below_sell_value: float = 100.0,
    dp_groww_component_per_sell: float | None = 16.5,
    dp_depository_component_per_sell: float | None = 3.5,
    slippage_bps_per_side: float = 2.0,
    notional_rupees: float = 100000.0,
) -> dict:
    """Estimate Groww NSE equity-delivery charges for a fixed rupee notional.

    Groww tariff values are configurable. The default DP value is the
    published standard ₹20 pre-GST sell charge; account-specific concessions
    (including the ₹19.75 depository component for women) can be supplied.
    Slippage is a scenario assumption, not a guaranteed fill estimate.
    """
    if (not np.isfinite(entry_price) or not np.isfinite(exit_price)
            or entry_price <= 0 or exit_price <= 0):
        raise ValueError("Entry and exit prices must be finite and positive")
    numeric_parameters = {
        "notional_rupees": notional_rupees,
        "stt_rate_each_side": stt_rate_each_side,
        "stamp_duty_buy_rate": stamp_duty_buy_rate,
        "exchange_rate_each_side": exchange_rate_each_side,
        "ipft_rate_each_side": ipft_rate_each_side,
        "sebi_rate_each_side": sebi_rate_each_side,
        "gst_rate": gst_rate,
        "brokerage_rate_each_side": brokerage_rate_each_side,
        "brokerage_cap_per_order": brokerage_cap_per_order,
        "brokerage_min_per_order": brokerage_min_per_order,
        "brokerage_min_rate": brokerage_min_rate,
        "dp_charge_per_sell": dp_charge_per_sell,
        "dp_free_below_sell_value": dp_free_below_sell_value,
        "slippage_bps_per_side": slippage_bps_per_side,
    }
    if dp_groww_component_per_sell is not None:
        numeric_parameters["dp_groww_component_per_sell"] = dp_groww_component_per_sell
    if dp_depository_component_per_sell is not None:
        numeric_parameters["dp_depository_component_per_sell"] = dp_depository_component_per_sell
    if any(not np.isfinite(value) for value in numeric_parameters.values()):
        raise ValueError("Cost parameters must be finite")
    if notional_rupees <= 0:
        raise ValueError("Notional must be positive")
    if any(value < 0 for key, value in numeric_parameters.items() if key != "notional_rupees"):
        raise ValueError("Cost rates and fixed charges cannot be negative")

    buy_turnover = float(notional_rupees)
    sell_turnover = buy_turnover * float(exit_price) / float(entry_price)
    brokerage = (
        _groww_brokerage(buy_turnover, brokerage_rate_each_side,
                         brokerage_cap_per_order, brokerage_min_per_order,
                         brokerage_min_rate)
        + _groww_brokerage(sell_turnover, brokerage_rate_each_side,
                           brokerage_cap_per_order, brokerage_min_per_order,
                           brokerage_min_rate)
    )
    stt = (buy_turnover + sell_turnover) * stt_rate_each_side
    stamp = buy_turnover * stamp_duty_buy_rate
    exchange = (buy_turnover + sell_turnover) * exchange_rate_each_side
    ipft = (buy_turnover + sell_turnover) * ipft_rate_each_side
    sebi = (buy_turnover + sell_turnover) * sebi_rate_each_side
    if dp_groww_component_per_sell is not None and dp_depository_component_per_sell is not None:
        # Groww waives its own DP component for sell value below ₹100; the
        # separate depository fee remains payable on the sell transaction.
        dp = float(dp_depository_component_per_sell)
        if sell_turnover >= dp_free_below_sell_value:
            dp += float(dp_groww_component_per_sell)
    else:
        # Backward-compatible aggregate fee behavior for custom legacy callers.
        dp = 0.0 if sell_turnover < dp_free_below_sell_value else float(dp_charge_per_sell)
    gst = gst_rate * (brokerage + exchange + ipft + sebi + dp)
    slippage = (buy_turnover + sell_turnover) * slippage_bps_per_side / 10000.0
    total = stt + stamp + exchange + ipft + sebi + brokerage + dp + gst + slippage
    gross_return = float(exit_price) / float(entry_price) - 1.0
    gross_pnl = buy_turnover * gross_return
    return {
        "gross_return": gross_return,
        "gross_pnl_rupees": gross_pnl,
        "stt_rupees": stt,
        "stamp_duty_rupees": stamp,
        "exchange_rupees": exchange,
        "ipft_rupees": ipft,
        "sebi_rupees": sebi,
        "brokerage_rupees": brokerage,
        "dp_rupees": dp,
        "gst_rupees": gst,
        "slippage_rupees": slippage,
        "total_cost_rupees": total,
        "net_pnl_rupees": gross_pnl - total,
        "net_return": (gross_pnl - total) / buy_turnover,
        "cost_return": total / buy_turnover,
    }


def reconcile_groww_contract_notes(
    observations: pd.DataFrame,
    *,
    tolerance_rupees: float = 0.05,
    cost_parameters: dict | None = None,
) -> pd.DataFrame:
    """Compare anonymised round-trip contract-note charges with the tariff model.

    Required input columns are entry_price, exit_price, notional_rupees and
    actual_* charge columns for brokerage, STT, stamp duty, exchange, IPFT,
    SEBI, DP and GST. Slippage is deliberately excluded because it is not a
    contract-note fee. This validates arithmetic only; it does not authenticate
    the uploaded contract notes or establish account-specific tariff terms.
    """
    actual_columns = {
        "actual_brokerage_rupees": "brokerage_rupees",
        "actual_stt_rupees": "stt_rupees",
        "actual_stamp_duty_rupees": "stamp_duty_rupees",
        "actual_exchange_rupees": "exchange_rupees",
        "actual_ipft_rupees": "ipft_rupees",
        "actual_sebi_rupees": "sebi_rupees",
        "actual_dp_rupees": "dp_rupees",
        "actual_gst_rupees": "gst_rupees",
    }
    required = {"entry_price", "exit_price", "notional_rupees", *actual_columns}
    missing = required.difference(observations.columns)
    if missing:
        raise ValueError(f"Contract-note observations missing columns: {sorted(missing)}")
    if not np.isfinite(tolerance_rupees) or tolerance_rupees < 0:
        raise ValueError("tolerance_rupees must be finite and non-negative")

    costs = dict(DEFAULT_DELIVERY_COSTS if cost_parameters is None else cost_parameters)
    costs["slippage_bps_per_side"] = 0.0
    rows = []
    for index, row in observations.iterrows():
        numeric = [row[column] for column in required]
        if any(pd.isna(value) or not np.isfinite(float(value)) for value in numeric):
            raise ValueError(f"Contract-note row {index} contains missing or non-finite values")
        if float(row["notional_rupees"]) <= 0:
            raise ValueError(f"Contract-note row {index} has non-positive notional")
        estimate = delivery_round_trip_cost(
            float(row["entry_price"]), float(row["exit_price"]),
            notional_rupees=float(row["notional_rupees"]), **costs,
        )
        result = row.to_dict()
        deltas = []
        for actual_column, estimated_key in actual_columns.items():
            expected = float(estimate[estimated_key])
            actual = float(row[actual_column])
            result[f"estimated_{estimated_key}"] = expected
            result[f"delta_{estimated_key}"] = actual - expected
            deltas.append(actual - expected)
        actual_total = sum(float(row[column]) for column in actual_columns)
        expected_total = sum(float(estimate[key]) for key in actual_columns.values())
        result["actual_total_charges_rupees"] = actual_total
        result["estimated_total_charges_rupees"] = expected_total
        result["total_delta_rupees"] = actual_total - expected_total
        result["within_tolerance"] = all(abs(delta) <= tolerance_rupees for delta in deltas)
        rows.append(result)
    return pd.DataFrame(rows, index=observations.index)


def add_delivery_costs(frame: pd.DataFrame, **costs) -> pd.DataFrame:
    """Attach gross/net per-trade returns and a rupee cost estimate."""
    if not {"close", "exit_price"}.issubset(frame.columns):
        raise ValueError("Frame must include close and exit_price")
    result = frame.copy()
    entries = result["entry_price"] if "entry_price" in result else result["close"]
    estimates = [
        delivery_round_trip_cost(entry, exit_price, **costs)
        if pd.notna(exit_price) and pd.notna(entry) else None
        for entry, exit_price in zip(entries, result["exit_price"])
    ]
    result["net_return"] = [
        estimate["net_return"] if estimate is not None else np.nan for estimate in estimates
    ]
    result["estimated_cost_return"] = [
        estimate["cost_return"] if estimate is not None else np.nan for estimate in estimates
    ]
    return result
