import pandas as pd
import pytest

from trader.costs import delivery_round_trip_cost
from trader.portfolio import simulate_overlapping_portfolio


def _candidates():
    return pd.DataFrame([
        {"symbol": "AAA", "score": .9, "entry_date": "2026-01-02", "exit_date": "2026-01-06",
         "entry_price": 100, "exit_price": 110, "net_return": .10},
        {"symbol": "BBB", "score": .8, "entry_date": "2026-01-02", "exit_date": "2026-01-05",
         "entry_price": 100, "exit_price": 95, "net_return": -.05},
        {"symbol": "CCC", "score": .7, "entry_date": "2026-01-05", "exit_date": "2026-01-08",
         "entry_price": 100, "exit_price": 105, "net_return": .05},
        {"symbol": "AAA", "score": .95, "entry_date": "2026-01-05", "exit_date": "2026-01-09",
         "entry_price": 100, "exit_price": 103, "net_return": .03},
    ])


def test_portfolio_respects_cash_capacity_and_overlapping_symbol():
    result = simulate_overlapping_portfolio(_candidates(), initial_capital=100_000, max_positions=3)
    assert result["trades"] == 3
    assert result["rejected"]["already_held"] == 1
    assert result["ending_equity"] > 100_000
    assert result["peak_gross_exposure"] <= 1.0


def test_portfolio_enforces_turnover_when_requested():
    data = _candidates()
    data["avg_daily_turnover"] = [1_000_000, 1_000_000, 1_000_000, 1_000_000]
    result = simulate_overlapping_portfolio(
        data, min_avg_daily_turnover=2_000_000, initial_capital=100_000,
    )
    assert result["trades"] == 0
    assert result["rejected"]["liquidity"] == 4


def test_liquidity_threshold_without_turnover_data_fails_closed():
    with pytest.raises(ValueError, match="avg_daily_turnover"):
        simulate_overlapping_portfolio(_candidates(), min_avg_daily_turnover=1_000_000)


def test_invalid_or_unresolved_rows_are_not_silently_traded():
    data = _candidates()
    data.loc[0, "exit_date"] = pd.NaT
    result = simulate_overlapping_portfolio(data)
    assert result["rejected"]["invalid"] == 1
    assert result["trades"] == 3



def test_turnover_participation_caps_position_notional():
    data = _candidates().iloc[[0]].copy()
    data["avg_daily_turnover"] = 10_000
    result = simulate_overlapping_portfolio(
        data, initial_capital=100_000, max_participation_rate=0.01,
    )
    assert result["trades"] == 1
    assert result["trade_log"][0]["notional"] == pytest.approx(100)
    assert result["liquidity_constraint_applied"] is True
    assert result["liquidity_data_available"] is True



def test_same_day_intraday_exit_does_not_fund_next_open_entry():
    data = pd.DataFrame([
        {"symbol": "AAA", "score": .9, "entry_date": "2026-01-02", "exit_date": "2026-01-05",
         "entry_price": 100, "exit_price": 110, "net_return": .10},
        {"symbol": "BBB", "score": .8, "entry_date": "2026-01-05", "exit_date": "2026-01-08",
         "entry_price": 100, "exit_price": 105, "net_return": .05},
    ])
    result = simulate_overlapping_portfolio(
        data, initial_capital=100_000, max_positions=1,
    )
    assert result["trades"] == 1
    assert result["rejected"]["capacity"] == 1



def test_event_simulator_uses_whole_shares_and_actual_notional_costs():
    data = _candidates().iloc[[0]].copy()
    data["entry_price"] = 103.0
    data["net_return"] = 0.99  # legacy field must not override execution-cost math
    result = simulate_overlapping_portfolio(
        data, initial_capital=100_000, max_positions=1,
        max_position_fraction=0.20,
    )
    trade = result["trade_log"][0]
    expected = delivery_round_trip_cost(
        103.0, 110.0, notional_rupees=194 * 103.0,
    )
    assert trade["shares"] == pytest.approx(194)
    assert trade["notional"] == pytest.approx(194 * 103.0)
    assert trade["cost_rupees"] == pytest.approx(expected["total_cost_rupees"])
    assert trade["net_return"] == pytest.approx(expected["net_return"])
    assert trade["net_return"] != pytest.approx(0.99)


def test_non_finite_scores_and_prices_are_rejected():
    data = _candidates().iloc[[0]].copy()
    data.loc[data.index[0], "score"] = float("inf")
    result = simulate_overlapping_portfolio(data)
    assert result["rejected"]["invalid"] == 1
    assert result["trades"] == 0



def test_event_simulator_enforces_sector_cap_when_enabled():
    data = _candidates().iloc[:3].copy()
    data["sector"] = "Financials"
    result = simulate_overlapping_portfolio(
        data, initial_capital=100_000, max_positions=5,
        max_position_fraction=0.20, max_sector_exposure_fraction=0.30,
    )
    assert result["rejected"]["sector_cap"] >= 1
    assert result["trades"] <= 2
    assert result["max_sector_exposure_fraction"] == pytest.approx(0.30)
