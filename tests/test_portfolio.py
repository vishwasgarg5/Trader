import pandas as pd
import pytest

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
    result = simulate_overlapping_portfolio(_candidates(), initial_capital=100_000, max_positions=2)
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
