from __future__ import annotations

import numpy as np
import pandas as pd

from trader.costs import DEFAULT_DELIVERY_COSTS, delivery_round_trip_cost


def simulate_overlapping_portfolio(
    candidates: pd.DataFrame,
    *,
    initial_capital: float = 1_000_000.0,
    max_positions: int = 5,
    max_position_fraction: float = 0.20,
    max_gross_exposure: float = 1.0,
    min_avg_daily_turnover: float | None = None,
    max_participation_rate: float = 0.01,
    cost_parameters: dict | None = None,
) -> dict:
    """Event-driven cash-funded delivery simulation with actual-notional costs.

    Required columns: symbol, score, entry_date, exit_date, entry_price,
    exit_price. The legacy net_return column is accepted but ignored: brokerage,
    statutory charges, DP and slippage are recomputed from each executed order's
    actual whole-share notional. Drawdown remains realised/event-date only; use
    portfolio_diagnostics for daily mark-to-market drawdown.
    """
    required = {"symbol", "score", "entry_date", "exit_date", "entry_price", "exit_price"}
    missing = required.difference(candidates.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if initial_capital <= 0 or max_positions < 1:
        raise ValueError("initial_capital and max_positions must be positive")
    if not 0 < max_position_fraction <= 1 or not 0 < max_gross_exposure <= 1:
        raise ValueError("position and gross exposure fractions must be in (0, 1]")
    if not 0 < max_participation_rate <= 1:
        raise ValueError("max_participation_rate must be in (0, 1]")
    costs = dict(DEFAULT_DELIVERY_COSTS if cost_parameters is None else cost_parameters)

    data = candidates.copy()
    for col in ("entry_date", "exit_date"):
        data[col] = pd.to_datetime(data[col], errors="coerce")
    for col in ("score", "entry_price", "exit_price"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data["symbol"] = data["symbol"].astype(str).str.strip().str.upper()
    valid = (
        data["symbol"].ne("") & data["entry_date"].notna() & data["exit_date"].notna()
        & (data["exit_date"] >= data["entry_date"])
        & data["score"].notna() & (data["entry_price"] > 0)
        & (data["exit_price"] > 0)
        & np.isfinite(data["entry_price"]) & np.isfinite(data["exit_price"])
    )
    invalid_rows = int((~valid).sum())
    data = data.loc[valid].copy()
    if data.empty:
        return {
            "status": "no_valid_candidates", "initial_capital": float(initial_capital),
            "ending_equity": float(initial_capital), "net_return": 0.0,
            "trades": 0, "rejected": {"invalid": invalid_rows},
        }

    liquidity_available = "avg_daily_turnover" in data.columns
    if min_avg_daily_turnover is not None and not liquidity_available:
        raise ValueError("Liquidity threshold requires avg_daily_turnover")
    if liquidity_available:
        data["avg_daily_turnover"] = pd.to_numeric(data["avg_daily_turnover"], errors="coerce")

    entries = {day: group.sort_values(["score", "symbol"], ascending=[False, True], kind="mergesort")
               for day, group in data.groupby("entry_date", sort=True)}
    exit_days = set(data["exit_date"])
    event_days = sorted(set(entries).union(exit_days))
    cash = float(initial_capital)
    positions: dict[str, dict] = {}
    trades = []
    rejected = {"capacity": 0, "already_held": 0, "cash": 0, "liquidity": 0, "invalid": invalid_rows}
    equity_peak = float(initial_capital)
    max_drawdown = 0.0
    gross_exposure_peak = 0.0

    for day in event_days:
        group = entries.get(day)
        if group is not None:
            for row in group.itertuples(index=False):
                symbol = row.symbol
                if symbol in positions:
                    rejected["already_held"] += 1
                    continue
                if len(positions) >= max_positions:
                    rejected["capacity"] += 1
                    continue
                if min_avg_daily_turnover is not None:
                    turnover = getattr(row, "avg_daily_turnover", np.nan)
                    if not np.isfinite(turnover) or turnover < min_avg_daily_turnover:
                        rejected["liquidity"] += 1
                        continue
                target_fraction = min(max_position_fraction, max_gross_exposure / max_positions)
                invested = sum(pos["notional"] for pos in positions.values())
                equity = cash + invested
                target_notional = min(equity * target_fraction, cash,
                                      max(0.0, equity * max_gross_exposure - invested))
                if liquidity_available:
                    turnover = getattr(row, "avg_daily_turnover", np.nan)
                    if not np.isfinite(turnover) or turnover <= 0:
                        rejected["liquidity"] += 1
                        continue
                    target_notional = min(target_notional, float(turnover) * max_participation_rate)
                if target_notional <= 0:
                    rejected["cash"] += 1
                    continue
                shares = float(np.floor(target_notional / float(row.entry_price)))
                executed_notional = shares * float(row.entry_price)
                if shares < 1 or executed_notional <= 0:
                    rejected["cash"] += 1
                    continue
                positions[symbol] = {
                    "entry_date": day, "exit_date": row.exit_date,
                    "entry_price": float(row.entry_price), "exit_price": float(row.exit_price),
                    "notional": float(executed_notional), "shares": shares,
                    "score": float(row.score), "exit_reason": getattr(row, "exit_reason", None),
                }
                cash -= executed_notional

        # Same-day exits remain reserved until after entries; a barrier exit
        # cannot fund a new next-open order on that same date.
        closing = [symbol for symbol, pos in positions.items() if pos["exit_date"] <= day]
        for symbol in closing:
            pos = positions.pop(symbol)
            estimate = delivery_round_trip_cost(
                pos["entry_price"], pos["exit_price"],
                **{**costs, "notional_rupees": pos["notional"]},
            )
            pnl = estimate["net_pnl_rupees"]
            cash += pos["notional"] + pnl
            trades.append({
                "symbol": symbol, "entry_date": str(pos["entry_date"].date()),
                "exit_date": str(pos["exit_date"].date()), "score": pos["score"],
                "notional": pos["notional"], "shares": pos["shares"],
                "gross_return": estimate["gross_return"],
                "net_return": estimate["net_return"], "net_pnl": pnl,
                "cost_rupees": estimate["total_cost_rupees"],
                "exit_reason": pos.get("exit_reason"),
            })

        invested = sum(pos["notional"] for pos in positions.values())
        equity = cash + invested
        gross_exposure_peak = max(gross_exposure_peak, invested / equity if equity > 0 else 0.0)
        equity_peak = max(equity_peak, equity)
        max_drawdown = max(max_drawdown, (equity_peak - equity) / equity_peak if equity_peak else 0.0)

    if positions:
        raise ValueError("Portfolio contains positions without a processed exit event")
    ending_equity = cash
    return {
        "status": "evaluated",
        "initial_capital": float(initial_capital),
        "ending_equity": float(ending_equity),
        "net_return": float(ending_equity / initial_capital - 1.0),
        "net_pnl": float(ending_equity - initial_capital),
        "trades": len(trades),
        "win_rate": float(np.mean([t["net_return"] > 0 for t in trades])) if trades else None,
        "average_trade_net_return": float(np.mean([t["net_return"] for t in trades])) if trades else None,
        "max_realized_equity_drawdown": float(max_drawdown),
        "peak_gross_exposure": float(gross_exposure_peak),
        "rejected": rejected,
        "liquidity_constraint_applied": liquidity_available,
        "liquidity_data_available": liquidity_available,
        "liquidity_warning": None if liquidity_available else
            "No enforceable liquidity cap was applied; turnover data and a threshold are required.",
        "drawdown_warning": "Drawdown uses realised equity at event dates and understates intra-trade mark-to-market drawdown.",
        "cost_accounting": "Groww charges recomputed from each actual whole-share order notional",
        "trade_log": trades,
    }
