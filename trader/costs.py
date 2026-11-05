from __future__ import annotations

import numpy as np
import pandas as pd

# NSE cash-market total exchange outflow (transaction charge + IPFT) from
# 2026-03-01: Rs 307 per crore per side = 0.00307%.
# Other statutory rates are the NSE rates applicable to equity delivery.
DEFAULT_DELIVERY_COSTS = {
    "stt_rate_each_side": 0.001,
    "stamp_duty_buy_rate": 0.00015,
    "exchange_rate_each_side": 0.0000307,
    "sebi_rate_each_side": 0.000001,
    "gst_rate": 0.18,
    "brokerage_rate_each_side": 0.0,
    "brokerage_cap_per_order": 20.0,
    "dp_charge_per_sell": 0.0,
    "slippage_bps_per_side": 2.0,
    "notional_rupees": 100000.0,
}


def delivery_round_trip_cost(
    entry_price: float,
    exit_price: float,
    *,
    stt_rate_each_side: float = 0.001,
    stamp_duty_buy_rate: float = 0.00015,
    exchange_rate_each_side: float = 0.0000307,
    sebi_rate_each_side: float = 0.000001,
    gst_rate: float = 0.18,
    brokerage_rate_each_side: float = 0.0,
    brokerage_cap_per_order: float = 20.0,
    dp_charge_per_sell: float = 0.0,
    slippage_bps_per_side: float = 2.0,
    notional_rupees: float = 100000.0,
) -> dict:
    """Estimate delivery-trade charges for a fixed rupee notional.

    Brokerage, DP and slippage are configurable. Defaults are a transparent
    scenario, not a broker contract note or guaranteed execution estimate.
    """
    if not np.isfinite(entry_price) or not np.isfinite(exit_price) or entry_price <= 0 or exit_price <= 0:
        raise ValueError("Entry and exit prices must be finite and positive")
    if notional_rupees <= 0 or brokerage_cap_per_order < 0 or dp_charge_per_sell < 0:
        raise ValueError("Notional must be positive and fixed charges non-negative")
    if min(stt_rate_each_side, stamp_duty_buy_rate, exchange_rate_each_side,
           sebi_rate_each_side, gst_rate, brokerage_rate_each_side, slippage_bps_per_side) < 0:
        raise ValueError("Cost rates cannot be negative")

    buy_turnover = float(notional_rupees)
    sell_turnover = buy_turnover * float(exit_price) / float(entry_price)
    brokerage = (
        min(buy_turnover * brokerage_rate_each_side, brokerage_cap_per_order)
        + min(sell_turnover * brokerage_rate_each_side, brokerage_cap_per_order)
    )
    stt = (buy_turnover + sell_turnover) * stt_rate_each_side
    stamp = buy_turnover * stamp_duty_buy_rate
    exchange = (buy_turnover + sell_turnover) * exchange_rate_each_side
    sebi = (buy_turnover + sell_turnover) * sebi_rate_each_side
    dp = float(dp_charge_per_sell)
    gst = gst_rate * (brokerage + exchange + sebi + dp)
    slippage = (buy_turnover + sell_turnover) * slippage_bps_per_side / 10000.0
    total = stt + stamp + exchange + sebi + brokerage + dp + gst + slippage
    gross_return = float(exit_price) / float(entry_price) - 1.0
    gross_pnl = buy_turnover * gross_return
    return {
        "gross_return": gross_return,
        "gross_pnl_rupees": gross_pnl,
        "stt_rupees": stt,
        "stamp_duty_rupees": stamp,
        "exchange_rupees": exchange,
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
