from __future__ import annotations

import numpy as np
import pandas as pd

from trader.costs import DEFAULT_DELIVERY_COSTS, delivery_round_trip_cost


def _normalise_daily_prices(daily_prices: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "symbol", "close"}
    missing = required.difference(daily_prices.columns)
    if missing:
        raise ValueError(f"daily_prices missing columns: {sorted(missing)}")
    prices = daily_prices.loc[:, ["date", "symbol", "close"]].copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices["symbol"] = prices["symbol"].astype(str).str.strip().str.upper()
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    # A malformed close invalidates the whole session for this price panel.
    # Keeping the other symbols on that date would create an inconsistent
    # cross-sectional calendar and can distort portfolio marks/benchmarks.
    invalid_close = (
        prices["close"].isna()
        | ~np.isfinite(prices["close"])
        | (prices["close"] <= 0)
    )
    invalid_dates = prices.loc[prices["date"].notna() & invalid_close, "date"].unique()
    if len(invalid_dates):
        prices = prices.loc[~prices["date"].isin(invalid_dates)]
    prices = prices.dropna(subset=["date", "symbol", "close"])
    prices = prices.loc[prices["symbol"] != ""]
    if prices.duplicated(["date", "symbol"]).any():
        raise ValueError("daily_prices contains duplicate date/symbol rows")
    return prices.pivot(index="date", columns="symbol", values="close").sort_index()


def simulate_mark_to_market_portfolio(
    candidates: pd.DataFrame,
    daily_prices: pd.DataFrame,
    *,
    initial_capital: float = 1_000_000.0,
    max_positions: int = 5,
    max_position_fraction: float = 0.20,
    max_gross_exposure: float = 1.0,
    max_participation_rate: float | None = None,
    cost_parameters: dict | None = None,
) -> dict:
    """Daily-close marked, cash-funded long-only simulation.

    Candidate rows are selected at signal_date and enter on entry_date. Open
    positions are valued from daily_prices close; on exit_date they are closed
    at the labelled exit_price. Missing intermediate closes are forward-filled
    per symbol and counted; no backfill is allowed. Fixed rupee costs are
    recomputed using each actual position notional.
    """
    required = {"symbol", "score", "signal_date", "entry_date", "exit_date",
                "entry_price", "exit_price", "net_return"}
    missing = required.difference(candidates.columns)
    if missing:
        raise ValueError(f"candidates missing columns: {sorted(missing)}")
    if initial_capital <= 0 or max_positions < 1:
        raise ValueError("initial_capital and max_positions must be positive")
    if not 0 < max_position_fraction <= 1 or not 0 < max_gross_exposure <= 1:
        raise ValueError("position and gross exposure fractions must be in (0, 1]")
    if max_participation_rate is not None and not 0 < max_participation_rate <= 1:
        raise ValueError("max_participation_rate must be in (0, 1]")
    if max_participation_rate is not None and "avg_daily_turnover" not in candidates.columns:
        raise ValueError("max_participation_rate requires avg_daily_turnover from NSE turnover history")
    if max_participation_rate is not None and not np.isfinite(
        pd.to_numeric(candidates["avg_daily_turnover"], errors="coerce")
    ).any():
        raise ValueError("No valid trailing NSE turnover history is available for liquidity constraints")

    prices = _normalise_daily_prices(daily_prices)
    data = candidates.copy()
    for col in ("signal_date", "entry_date", "exit_date"):
        data[col] = pd.to_datetime(data[col], errors="coerce")
    for col in ("score", "entry_price", "exit_price", "net_return"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data["symbol"] = data["symbol"].astype(str).str.strip().str.upper()
    valid = (data["symbol"].ne("") & data["signal_date"].notna()
             & data["entry_date"].notna() & data["exit_date"].notna()
             & (data["exit_date"] >= data["entry_date"])
             & (data["entry_price"] > 0) & (data["exit_price"] > 0)
             & data["score"].notna() & np.isfinite(data["score"])
             & data["entry_price"].map(np.isfinite)
             & data["exit_price"].map(np.isfinite)
             & data["net_return"].map(np.isfinite))
    invalid = int((~valid).sum())
    data = data.loc[valid].copy()
    if data.empty:
        return {"status": "no_valid_candidates", "initial_capital": initial_capital,
                "ending_equity": initial_capital, "net_return": 0.0, "trades": 0,
                "max_daily_drawdown": 0.0, "invalid_candidates": invalid}
    if not set(data["symbol"]).issubset(set(prices.columns)):
        absent = sorted(set(data["symbol"]) - set(prices.columns))
        raise ValueError(f"daily_prices missing candidate symbols: {absent[:10]}")

    # Entry dates must be represented in the panel; exits use labelled barrier
    # prices because gap/target/stop execution can differ from daily close.
    calendar = prices.index
    first_day, last_day = data["entry_date"].min(), data["exit_date"].max()
    calendar = calendar[(calendar >= first_day) & (calendar <= last_day)]
    if calendar.empty:
        raise ValueError("daily_prices does not cover candidate holding dates")
    if not set(data["entry_date"]).issubset(set(calendar)):
        raise ValueError("daily_prices is missing one or more candidate entry dates")
    if not set(data["exit_date"]).issubset(set(calendar)):
        raise ValueError("daily_prices is missing one or more candidate exit dates")
    data_by_entry = {
        day: group.sort_values(["score", "symbol"], ascending=[False, True], kind="mergesort")
        for day, group in data.groupby("entry_date", sort=True)
    }
    cash = float(initial_capital)
    positions: dict[str, dict] = {}
    trade_log = []
    daily_rows = []
    rejected = {"capacity": 0, "already_held": 0, "cash": 0, "liquidity": 0}
    stale_marks = 0
    peak_equity = float(initial_capital)
    max_drawdown = 0.0
    peak_exposure = average_exposure_sum = 0.0
    peak_sector_exposure = 0.0
    exposure_days = 0
    costs = dict(DEFAULT_DELIVERY_COSTS if cost_parameters is None else cost_parameters)

    for day in calendar:
        for row in data_by_entry.get(day, pd.DataFrame()).itertuples(index=False):
            symbol = row.symbol
            if symbol in positions:
                rejected["already_held"] += 1
                continue
            if len(positions) >= max_positions:
                rejected["capacity"] += 1
                continue
            invested = sum(p["notional"] for p in positions.values())
            equity_before = cash + sum(p["shares"] * p["last_price"] for p in positions.values())
            target = min(equity_before * max_position_fraction,
                         equity_before * max_gross_exposure / max_positions,
                         cash, max(0.0, equity_before * max_gross_exposure - invested))
            if max_participation_rate is not None:
                turnover = pd.to_numeric(pd.Series([getattr(row, "avg_daily_turnover", np.nan)]),
                                         errors="coerce").iloc[0]
                if not np.isfinite(turnover) or turnover <= 0:
                    rejected["liquidity"] += 1
                    continue
                target = min(target, turnover * max_participation_rate)
            if target <= 0:
                rejected["cash"] += 1
                continue
            # NSE cash equities trade in whole shares. Round down the order
            # quantity and use the resulting executed notional for cash,
            # exposure and per-order charges.
            shares = float(np.floor(target / float(row.entry_price)))
            executed_notional = shares * float(row.entry_price)
            if shares < 1 or executed_notional <= 0:
                rejected["cash"] += 1
                continue
            cash -= executed_notional
            positions[symbol] = {
                "signal_date": row.signal_date, "entry_date": day,
                "exit_date": row.exit_date, "entry_price": float(row.entry_price),
                "exit_price": float(row.exit_price), "notional": float(executed_notional),
                "shares": shares,
                "last_price": float(row.entry_price), "score": float(row.score),
                "fallback_net_return": float(row.net_return),
                "sector": getattr(row, "sector", None),
            }

        for symbol, position in list(positions.items()):
            if position["exit_date"] <= day:
                exit_price = position["exit_price"]
                estimate = delivery_round_trip_cost(
                    position["entry_price"], exit_price,
                    **{**costs, "notional_rupees": position["notional"]},
                )
                net_pnl = estimate["net_pnl_rupees"]
                cash += position["notional"] + net_pnl
                trade_log.append({
                    "symbol": symbol, "signal_date": str(position["signal_date"].date()),
                    "entry_date": str(position["entry_date"].date()),
                    "exit_date": str(position["exit_date"].date()),
                    "notional": position["notional"], "shares": position["shares"], "score": position["score"],
                    "gross_return": estimate["gross_return"],
                    "net_return": estimate["net_return"], "net_pnl": net_pnl,
                    "cost_rupees": estimate["total_cost_rupees"],
                    "sector": position.get("sector"),
                })
                del positions[symbol]
                continue
            if symbol in prices.columns:
                mark = prices.at[day, symbol] if day in prices.index else np.nan
                if pd.notna(mark) and np.isfinite(mark) and mark > 0:
                    position["last_price"] = float(mark)
                else:
                    stale_marks += 1

        market_value = sum(p["shares"] * p["last_price"] for p in positions.values())
        equity = cash + market_value
        exposure = market_value / equity if equity > 0 else 0.0
        sector_values = {}
        for position in positions.values():
            sector = position.get("sector")
            if sector:
                sector_values[sector] = sector_values.get(sector, 0.0) + (
                    position["shares"] * position["last_price"]
                )
        sector_exposures = {
            sector: value / equity for sector, value in sorted(sector_values.items())
        } if equity > 0 else {}
        if sector_exposures:
            peak_sector_exposure = max(peak_sector_exposure, max(sector_exposures.values()))
        peak_exposure = max(peak_exposure, exposure)
        average_exposure_sum += exposure
        exposure_days += 1
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        daily_rows.append({"date": str(day.date()), "cash": cash,
                           "market_value": market_value, "equity": equity,
                           "gross_exposure": exposure, "sector_exposure": sector_exposures,
                           "max_sector_exposure": max(sector_exposures.values()) if sector_exposures else 0.0,
                           "drawdown": drawdown})

    if positions:
        raise ValueError("Daily price calendar ended with open positions; extend the price panel")
    ending = cash
    returns = [trade["net_return"] for trade in trade_log]
    symbol_allocations = {}
    sector_allocations = {}
    total_traded_notional = sum(trade["notional"] for trade in trade_log)
    for trade in trade_log:
        symbol_allocations[trade["symbol"]] = symbol_allocations.get(trade["symbol"], 0.0) + trade["notional"]
        if trade.get("sector"):
            sector_allocations[trade["sector"]] = sector_allocations.get(trade["sector"], 0.0) + trade["notional"]
    return {
        "status": "evaluated", "initial_capital": float(initial_capital),
        "ending_equity": float(ending), "net_return": float(ending / initial_capital - 1),
        "net_pnl": float(ending - initial_capital), "trades": len(trade_log),
        "win_rate": float(np.mean(np.asarray(returns) > 0)) if returns else None,
        "average_trade_net_return": float(np.mean(returns)) if returns else None,
        "max_daily_drawdown": float(max_drawdown),
        "peak_gross_exposure": float(peak_exposure),
        "peak_sector_exposure": float(peak_sector_exposure),
        "average_gross_exposure": float(average_exposure_sum / exposure_days) if exposure_days else 0.0,
        "exposure_days": exposure_days, "stale_daily_marks": stale_marks,
        "invalid_candidates": invalid, "rejected": rejected,
        "cost_accounting": "recomputed from actual position notional",
        "traded_notional_share_by_symbol": {
            key: value / total_traded_notional for key, value in sorted(symbol_allocations.items())
        } if total_traded_notional else {},
        "traded_notional_share_by_sector": {
            key: value / total_traded_notional for key, value in sorted(sector_allocations.items())
        } if total_traded_notional and sector_allocations else None,
        "sector_concentration_note": "Sector concentration is reported only when a sector column is supplied." if not sector_allocations else None,
        "daily_equity": daily_rows, "trade_log": trade_log,
    }


def index_benchmarks(
    daily_equity: list[dict],
    daily_prices: pd.DataFrame,
    *,
    index_symbol: str = "^NSEI",
) -> dict:
    """Calculate buy-and-hold and daily exposure-matched index comparators."""
    prices = _normalise_daily_prices(daily_prices)
    if index_symbol not in prices.columns:
        return {"status": "unavailable", "reason": f"{index_symbol} is absent from daily_prices"}
    equity = pd.DataFrame(daily_equity)
    if equity.empty:
        return {"status": "unavailable", "reason": "No daily portfolio equity observations"}
    equity["date"] = pd.to_datetime(equity["date"])
    series = prices[index_symbol].dropna()
    aligned = pd.DataFrame({"index_close": series}).join(
        equity.set_index("date")[["gross_exposure"]], how="inner"
    ).dropna()
    if len(aligned) < 2:
        return {"status": "unavailable", "reason": "Fewer than two common index/portfolio dates"}
    index_returns = aligned["index_close"].pct_change().fillna(0.0)
    buy_hold_curve = (1.0 + index_returns).cumprod()
    buy_hold_dd = buy_hold_curve / buy_hold_curve.cummax() - 1.0
    # Use prior close exposure for the next close-to-close index return.
    matched_returns = aligned["gross_exposure"].shift(1).fillna(0.0) * index_returns
    matched_curve = (1.0 + matched_returns).cumprod()
    matched_dd = matched_curve / matched_curve.cummax() - 1.0
    return {
        "status": "evaluated", "index_symbol": index_symbol,
        "start_date": str(aligned.index.min().date()),
        "end_date": str(aligned.index.max().date()),
        "buy_and_hold": {
            "net_return_before_index_costs": float(buy_hold_curve.iloc[-1] - 1.0),
            "max_drawdown": float(-buy_hold_dd.min()),
        },
        "exposure_matched": {
            "net_return_before_index_costs": float(matched_curve.iloc[-1] - 1.0),
            "max_drawdown": float(-matched_dd.min()),
            "method": "daily index return multiplied by prior-day strategy gross exposure",
        },
    }


def random_pick_monte_carlo(
    eligible_candidates: pd.DataFrame,
    daily_prices: pd.DataFrame,
    *,
    simulations: int = 300,
    seed: int = 42052,
    picks_per_signal_date: int = 5,
    **portfolio_kwargs,
) -> dict:
    """Compare model ranking with reproducible random picks from identical pools."""
    if simulations < 1 or picks_per_signal_date < 1:
        raise ValueError("simulations and picks_per_signal_date must be positive")
    required = {"signal_date", "symbol"}
    missing = required.difference(eligible_candidates.columns)
    if missing:
        raise ValueError(f"eligible_candidates missing columns: {sorted(missing)}")
    rng = np.random.default_rng(seed)
    groups = [(day, group) for day, group in eligible_candidates.groupby("signal_date", sort=True)]
    results = []
    for run in range(simulations):
        selected = []
        for day, group in groups:
            count = min(picks_per_signal_date, len(group))
            indices = rng.choice(len(group), size=count, replace=False)
            selected.append(group.iloc[indices])
        sample = pd.concat(selected, axis=0) if selected else eligible_candidates.iloc[0:0]
        result = simulate_mark_to_market_portfolio(sample, daily_prices, **portfolio_kwargs)
        results.append({
            "simulation": run, "net_return": result["net_return"],
            "max_daily_drawdown": result["max_daily_drawdown"],
            "trades": result["trades"],
            "average_gross_exposure": result["average_gross_exposure"],
            "peak_gross_exposure": result["peak_gross_exposure"],
        })
    returns = np.asarray([r["net_return"] for r in results], dtype=float)
    drawdowns = np.asarray([r["max_daily_drawdown"] for r in results], dtype=float)
    return {
        "simulations": simulations, "seed": seed,
        "selection": "uniform without replacement within each signal date; same eligible pool and simulator",
        "net_return_distribution": {
            "mean": float(returns.mean()), "median": float(np.median(returns)),
            "p05": float(np.quantile(returns, 0.05)), "p95": float(np.quantile(returns, 0.95)),
            "fraction_below_zero": float(np.mean(returns < 0)),
        },
        "max_daily_drawdown_distribution": {
            "mean": float(drawdowns.mean()), "median": float(np.median(drawdowns)),
            "p05": float(np.quantile(drawdowns, 0.05)), "p95": float(np.quantile(drawdowns, 0.95)),
        },
        "runs": results,
    }
