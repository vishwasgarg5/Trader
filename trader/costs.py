from __future__ import annotations

import numpy as np
import pandas as pd

# NSE cash-market exchange transaction charge (0.00297%) and IPFT (0.0001%)
# are modelled separately. Groww's published equity-delivery tariff
# checked 2026-11-05: brokerage min(₹20, 0.1% of order value), minimum
# lower of ₹5 or 2.5% of order value; delivery sell DP ₹20 (₹16.50 Groww
# + ₹3.50 depository) unless sell value is below ₹100. GST applies to
# brokerage, exchange/IPFT/SEBI and DP charges. Slippage remains a scenario input.
DEFAULT_DELIVERY_COSTS = {
    "stt_rate_each_side": 0.001,
    "stamp_duty_buy_rate": 0.00015,
    "exchange_rate_each_side": 0.0000297,
    "ipft_rate_each_side": 0.000001,
    "sebi_rate_each_side": 0.000001,
    "gst_rate": 0.18,
    "brokerage_rate_each_side": 0.001,
    "brokerage_cap_per_order": 20.0,
    "brokerage_min_per_order": 5.0,
    "brokerage_min_rate": 0.025,
    "dp_charge_per_sell": 20.0,
    "dp_free_below_sell_value": 100.0,
    "slippage_bps_per_side": 2.0,
    "notional_rupees": 100000.0,
}


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
    if (not np.isfinite(notional_rupees) or notional_rupees <= 0
            or brokerage_cap_per_order < 0 or brokerage_min_per_order < 0
            or dp_charge_per_sell < 0 or dp_free_below_sell_value < 0):
        raise ValueError("Notional must be positive and fixed charges non-negative")
    if min(stt_rate_each_side, stamp_duty_buy_rate, exchange_rate_each_side,
           ipft_rate_each_side, sebi_rate_each_side, gst_rate, brokerage_rate_each_side,
           brokerage_min_rate, slippage_bps_per_side) < 0:
        raise ValueError("Cost rates cannot be negative")

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
