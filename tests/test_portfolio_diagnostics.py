import pandas as pd
import pytest

from trader.costs import delivery_round_trip_cost
from trader.portfolio_diagnostics import (
    _normalise_daily_prices, index_benchmarks, random_pick_monte_carlo, simulate_mark_to_market_portfolio,
)


def _prices():
    return pd.DataFrame([
        {"date": "2026-01-02", "symbol": "AAA", "close": 100},
        {"date": "2026-01-05", "symbol": "AAA", "close": 70},
        {"date": "2026-01-06", "symbol": "AAA", "close": 90},
        {"date": "2026-01-07", "symbol": "AAA", "close": 95},
        {"date": "2026-01-02", "symbol": "BBB", "close": 100},
        {"date": "2026-01-05", "symbol": "BBB", "close": 102},
        {"date": "2026-01-06", "symbol": "BBB", "close": 104},
        {"date": "2026-01-07", "symbol": "BBB", "close": 106},
    ])


def _candidates():
    return pd.DataFrame([
        {"symbol": "AAA", "score": .9, "signal_date": "2026-01-01",
         "entry_date": "2026-01-02", "exit_date": "2026-01-06",
         "entry_price": 100, "exit_price": 90, "net_return": -.10},
        {"symbol": "BBB", "score": .8, "signal_date": "2026-01-01",
         "entry_date": "2026-01-02", "exit_date": "2026-01-07",
         "entry_price": 100, "exit_price": 106, "net_return": .06},
    ])


def test_daily_mark_to_market_captures_open_position_loss():
    result = simulate_mark_to_market_portfolio(
        _candidates().iloc[[0]], _prices(), initial_capital=100_000,
        max_positions=1,
    )
    assert result["trades"] == 1
    assert result["max_daily_drawdown"] >= .05
    assert result["daily_equity"][1]["equity"] < 100_000
    assert result["average_gross_exposure"] > 0
    assert result["peak_gross_exposure"] > 0


def test_actual_notional_is_used_for_fixed_and_variable_costs():
    costs = {
        "stt_rate_each_side": .001, "stamp_duty_buy_rate": .00015,
        "exchange_rate_each_side": .0000307, "sebi_rate_each_side": .000001,
        "gst_rate": .18, "brokerage_rate_each_side": .001,
        "brokerage_cap_per_order": 20, "dp_charge_per_sell": 12,
        "slippage_bps_per_side": 2,
    }
    result = simulate_mark_to_market_portfolio(
        _candidates().iloc[[0]], _prices(), initial_capital=100_000,
        max_positions=1, cost_parameters=costs,
    )
    expected = delivery_round_trip_cost(
        100, 90, **costs, notional_rupees=20_000,
    )
    assert result["trade_log"][0]["notional"] == pytest.approx(20_000)
    assert result["trade_log"][0]["cost_rupees"] == pytest.approx(expected["total_cost_rupees"])


def test_random_pick_harness_is_reproducible_and_uses_same_portfolio_engine():
    candidates = pd.concat([_candidates(), _candidates().assign(
        symbol=lambda x: x["symbol"].replace({"AAA": "BBB", "BBB": "AAA"}),
        score=lambda x: 1 - x["score"],
    )], ignore_index=True)
    first = random_pick_monte_carlo(
        candidates, _prices(), simulations=12, seed=17, initial_capital=100_000,
    )
    second = random_pick_monte_carlo(
        candidates, _prices(), simulations=12, seed=17, initial_capital=100_000,
    )
    assert first == second
    assert first["simulations"] == 12
    assert len(first["runs"]) == 12
    assert first["net_return_distribution"]["p05"] <= first["net_return_distribution"]["p95"]


def test_missing_daily_price_symbol_fails_closed():
    with pytest.raises(ValueError, match="missing candidate symbols"):
        simulate_mark_to_market_portfolio(
            _candidates(), _prices().query("symbol == 'AAA'"),
        )



def test_index_benchmarks_include_buy_hold_and_exposure_matched_results():
    prices = _prices()
    prices = pd.concat([prices, pd.DataFrame([
        {"date": "2026-01-02", "symbol": "^NSEI", "close": 100},
        {"date": "2026-01-05", "symbol": "^NSEI", "close": 95},
        {"date": "2026-01-06", "symbol": "^NSEI", "close": 98},
        {"date": "2026-01-07", "symbol": "^NSEI", "close": 101},
    ])], ignore_index=True)
    result = simulate_mark_to_market_portfolio(
        _candidates().iloc[[0]], prices, initial_capital=100_000, max_positions=1,
    )
    benchmark = index_benchmarks(result["daily_equity"], prices)
    assert benchmark["status"] == "evaluated"
    assert benchmark["buy_and_hold"]["net_return_before_index_costs"] == pytest.approx(-0.02)
    assert benchmark["exposure_matched"]["method"].startswith("daily index return")



def test_delivery_simulator_rounds_order_quantity_to_whole_shares():
    candidate = _candidates().iloc[[0]].copy()
    candidate["entry_price"] = 103.0
    result = simulate_mark_to_market_portfolio(
        candidate, _prices(), initial_capital=100_000,
        max_positions=1, max_position_fraction=0.20,
    )
    trade = result["trade_log"][0]
    assert trade["shares"] == pytest.approx(194)
    assert trade["notional"] == pytest.approx(194 * 103.0)
    assert trade["notional"] <= 20_000


def test_mark_to_market_rejects_non_finite_candidate_values():
    candidate = _candidates().iloc[[0]].copy()
    candidate.loc[candidate.index[0], "score"] = float("inf")
    result = simulate_mark_to_market_portfolio(candidate, _prices())
    assert result["status"] == "no_valid_candidates"
    assert result["invalid_candidates"] == 1


def test_daily_price_normalizer_drops_non_finite_closes():
    prices = _prices().copy()
    prices.loc[0, "close"] = float("inf")
    normalised = _normalise_daily_prices(prices)
    assert pd.Timestamp("2026-01-02") not in normalised.index
