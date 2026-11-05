from __future__ import annotations

import numpy as np
import pandas as pd


def simulate_overlapping_portfolio(
    candidates: pd.DataFrame,
    *,
    initial_capital: float = 1_000_000.0,
    max_positions: int = 5,
    max_position_fraction: float = 0.20,
    max_gross_exposure: float = 1.0,
    min_avg_daily_turnover: float | None = None,
    max_participation_rate: float = 0.01,
) -> dict:
    """Event-driven long-only portfolio simulation using OOS-ranked trade candidates.

    Required columns: symbol, score, entry_date, exit_date, entry_price,
    exit_price, net_return. net_return must already include the configured
    per-trade costs. Positions are cash-funded, equal-weight target sized,
    cannot overlap in the same symbol, and are closed on the label exit date.
    Liquidity is enforced only when a turnover field and threshold are supplied.
    """
    required = {"symbol", "score", "entry_date", "exit_date", "entry_price", "exit_price", "net_return"}
    missing = required.difference(candidates.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if initial_capital <= 0 or max_positions < 1:
        raise ValueError("initial_capital and max_positions must be positive")
    if not 0 < max_position_fraction <= 1 or not 0 < max_gross_exposure <= 1:
        raise ValueError("position and gross exposure fractions must be in (0, 1]")
    if not 0 < max_participation_rate <= 1:
        raise ValueError("max_participation_rate must be in (0, 1]")

    data = candidates.copy()
    for col in ("entry_date", "exit_date"):
        data[col] = pd.to_datetime(data[col], errors="coerce")
    for col in ("score", "entry_price", "exit_price", "net_return"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data["symbol"] = data["symbol"].astype(str).str.strip().str.upper()
    valid = (
        data["symbol"].ne("") & data["entry_date"].notna() & data["exit_date"].notna()
        & (data["exit_date"] >= data["entry_date"])
        & data["score"].notna() & (data["entry_price"] > 0)
        & (data["exit_price"] > 0) & data["net_return"].notna()
        & np.isfinite(data["net_return"])
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
        # Exit first so capital released at today's open can be reused.
        closing = [symbol for symbol, pos in positions.items() if pos["exit_date"] <= day]
        for symbol in closing:
            pos = positions.pop(symbol)
            pnl = pos["notional"] * pos["net_return"]
            cash += pos["notional"] + pnl
            trades.append({
                "symbol": symbol, "entry_date": str(pos["entry_date"].date()),
                "exit_date": str(pos["exit_date"].date()), "score": pos["score"],
                "notional": pos["notional"], "net_return": pos["net_return"],
                "net_pnl": pnl, "exit_reason": pos.get("exit_reason"),
            })

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
                positions[symbol] = {
                    "entry_date": day, "exit_date": row.exit_date,
                    "notional": float(target_notional), "net_return": float(row.net_return),
                    "score": float(row.score), "exit_reason": getattr(row, "exit_reason", None),
                }
                cash -= target_notional

        invested = sum(pos["notional"] for pos in positions.values())
        equity = cash + invested
        gross_exposure_peak = max(gross_exposure_peak, invested / equity if equity > 0 else 0.0)
        equity_peak = max(equity_peak, equity)
        max_drawdown = max(max_drawdown, (equity_peak - equity) / equity_peak if equity_peak else 0.0)

    # All valid trades should have an exit event. This guard prevents silent
    # treatment of unresolved open positions as realised results.
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
        "liquidity_constraint_applied": min_avg_daily_turnover is not None,
        "liquidity_data_available": liquidity_available,
        "liquidity_warning": None if min_avg_daily_turnover is not None else
            "No enforceable liquidity cap was applied; turnover data and a threshold are required.",
        "drawdown_warning": "Drawdown uses realised equity at event dates and understates intra-trade mark-to-market drawdown.",
        "trade_log": trades,
    }
