import pandas as pd
import pytest

import json

from trader.costs import DEFAULT_DELIVERY_COSTS, load_groww_delivery_costs
from trader.delivery import parse_full_bhavcopy
from trader.portfolio_diagnostics import simulate_mark_to_market_portfolio
from trader.research import merge_delivery_percentages


def test_nse_bhavcopy_parses_rupee_turnover():
    payload = (
        "SYMBOL,SERIES,DATE1,DELIV_PER,TURNOVER_LACS\n"
        "AAA,EQ,05-Nov-2026,52.5,125.5\n"
    ).encode()
    result = parse_full_bhavcopy(payload, pd.Timestamp("2026-11-05"), {"AAA"})
    assert result.loc[0, "turnover_rupees"] == pytest.approx(12_550_000)


def test_trailing_turnover_is_20_session_mean(tmp_path):
    dates = pd.bdate_range("2026-01-01", periods=20)
    frame = pd.DataFrame({"symbol": ["AAA.NS"] * 20}, index=dates)
    path = tmp_path / "delivery.csv"
    pd.DataFrame({
        "date": dates, "symbol": ["AAA.NS"] * 20,
        "delivery_pct": [50.0] * 20, "turnover_rupees": range(1, 21),
    }).to_csv(path, index=False)
    result = merge_delivery_percentages(frame, path)
    assert result["avg_daily_turnover"].iloc[-1] == pytest.approx(10.5)
    assert result["avg_daily_turnover"].iloc[:19].isna().all()


def _daily_prices():
    return pd.DataFrame([
        {"date": "2026-01-02", "symbol": "AAA", "close": 100},
        {"date": "2026-01-05", "symbol": "AAA", "close": 95},
        {"date": "2026-01-06", "symbol": "AAA", "close": 90},
    ])


def _candidate():
    return pd.DataFrame([{
        "symbol": "AAA", "score": 0.9, "signal_date": "2026-01-01",
        "entry_date": "2026-01-02", "exit_date": "2026-01-06",
        "entry_price": 100, "exit_price": 90, "net_return": -0.10,
        "avg_daily_turnover": 5_000_000, "sector": "Financial Services",
    }])


def test_mark_to_market_liquidity_cap_and_sector_exposure():
    result = simulate_mark_to_market_portfolio(
        _candidate(), _daily_prices(), initial_capital=100_000,
        max_positions=1, max_participation_rate=0.01,
    )
    assert result["trades"] == 1
    assert result["trade_log"][0]["notional"] <= 50_000
    assert result["peak_sector_exposure"] > 0
    assert any(row["sector_exposure"].get("Financial Services", 0) > 0
               for row in result["daily_equity"])


def test_mark_to_market_liquidity_fails_closed_without_turnover():
    candidate = _candidate().drop(columns=["avg_daily_turnover"])
    with pytest.raises(ValueError, match="NSE turnover history"):
        simulate_mark_to_market_portfolio(
            candidate, _daily_prices(), max_participation_rate=0.01,
        )



def test_groww_cost_defaults_are_loaded_from_the_profile():
    profile_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "config" / "broker_costs_groww.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    expected_dp = profile["dp"]["groww_component"] + profile["dp"]["depository_component_standard"]
    assert DEFAULT_DELIVERY_COSTS["dp_charge_per_sell"] == pytest.approx(expected_dp)
    assert DEFAULT_DELIVERY_COSTS["brokerage_cap_per_order"] == profile["brokerage"]["cap_per_executed_order"]
    assert DEFAULT_DELIVERY_COSTS["stt_rate_each_side"] == profile["statutory_and_exchange"]["stt_each_side"]


def test_groww_cost_loader_rejects_inconsistent_dp_components(tmp_path):
    profile_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "config" / "broker_costs_groww.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["dp"]["standard_pre_gst_total"] += 1
    invalid_path = tmp_path / "invalid-costs.json"
    invalid_path.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(ValueError, match="DP components"):
        load_groww_delivery_costs(invalid_path)


def test_groww_cost_loader_supports_account_specific_dp_component(tmp_path):
    profile_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "config" / "broker_costs_groww.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["dp"]["depository_component_standard"] = 3.25
    profile["dp"]["standard_pre_gst_total"] = 19.75
    custom_path = tmp_path / "custom-costs.json"
    custom_path.write_text(json.dumps(profile), encoding="utf-8")
    assert load_groww_delivery_costs(custom_path)["dp_charge_per_sell"] == pytest.approx(19.75)
