import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trader.costs import delivery_round_trip_cost
from trader.pilot_execution import (
    PILOT_MAX_PARTICIPATION, assess_pilot_liquidity, cap_pilot_fill,
    pilot_delivery_round_trip_cost, pilot_slippage_bps,
)


def test_registered_slippage_curve_at_reference_and_cap():
    assert pilot_slippage_bps(0.01) == pytest.approx(40.0)
    assert pilot_slippage_bps(0.02) == pytest.approx(15 + 25 * np.sqrt(2))
    assert pilot_slippage_bps(0.01, stress_multiplier=1.5) == pytest.approx(60.0)


@pytest.mark.parametrize("participation", [0, -0.01, 0.020001, np.nan, np.inf])
def test_slippage_rejects_invalid_or_over_limit_participation(participation):
    with pytest.raises(ValueError):
        pilot_slippage_bps(participation)


def test_pilot_delivery_cost_applies_registered_slippage_and_actual_notional():
    estimate = pilot_delivery_round_trip_cost(
        100.0, 105.0, notional_rupees=250_000.0,
        participation_fraction=0.01,
    )
    expected = delivery_round_trip_cost(
        100.0, 105.0, notional_rupees=250_000.0,
        slippage_bps_per_side=40.0,
    )
    assert estimate["slippage_bps_per_side"] == pytest.approx(40.0)
    assert estimate["slippage_rupees"] == pytest.approx(expected["slippage_rupees"])
    assert estimate["total_cost_rupees"] == pytest.approx(expected["total_cost_rupees"])
    assert estimate["participation_fraction"] == pytest.approx(0.01)
    assert estimate["slippage_basis"] == "registered_pilot_scenario_not_observed_execution"


def test_pilot_delivery_cost_stress_multiplier_changes_slippage_only():
    base = pilot_delivery_round_trip_cost(
        100.0, 100.0, notional_rupees=100_000.0,
        participation_fraction=0.01,
    )
    stressed = pilot_delivery_round_trip_cost(
        100.0, 100.0, notional_rupees=100_000.0,
        participation_fraction=0.01, stress_multiplier=1.5,
    )
    assert stressed["slippage_bps_per_side"] == pytest.approx(60.0)
    assert stressed["slippage_rupees"] == pytest.approx(base["slippage_rupees"] * 1.5)
    assert stressed["brokerage_rupees"] == pytest.approx(base["brokerage_rupees"])
    assert stressed["stt_rupees"] == pytest.approx(base["stt_rupees"])


def test_pilot_delivery_cost_rejects_missing_or_invalid_notional():
    with pytest.raises(ValueError, match="notional_rupees"):
        pilot_delivery_round_trip_cost(
            100, 100, notional_rupees=0, participation_fraction=0.01,
        )


def test_liquidity_uses_twenty_sessions_and_ignores_future_rows():
    dates = pd.bdate_range("2026-01-01", periods=21)
    frame = pd.DataFrame({"date": dates, "traded_value_rupees": [60_000_000.0] * 20 + [1.0]})
    result = assess_pilot_liquidity(frame, as_of=dates[19])
    assert result["status"] == "PASS"
    assert result["observations"] == 20
    assert result["median_turnover_rupees"] == pytest.approx(60_000_000.0)
    assert result["window_end"] == dates[19].date().isoformat()


def test_liquidity_fails_closed_when_history_is_incomplete():
    frame = pd.DataFrame({"date": pd.bdate_range("2026-01-01", periods=19),
                          "traded_value_rupees": [100_000_000.0] * 19})
    result = assess_pilot_liquidity(frame, as_of="2026-02-01")
    assert result["status"] == "UNRESOLVED_INSUFFICIENT_HISTORY"
    assert result["eligible"] is False


def test_liquidity_rejects_duplicate_sessions():
    dates = list(pd.bdate_range("2026-01-01", periods=19)) + [pd.Timestamp("2026-01-01")]
    frame = pd.DataFrame({"date": dates, "traded_value_rupees": [100_000_000.0] * 20})
    with pytest.raises(ValueError, match="duplicate"):
        assess_pilot_liquidity(frame, as_of="2026-02-01")


def test_liquidity_fails_when_median_is_below_registered_floor():
    frame = pd.DataFrame({"date": pd.bdate_range("2026-01-01", periods=20),
                          "traded_value_rupees": [49_000_000.0] * 20})
    result = assess_pilot_liquidity(frame, as_of="2026-02-01")
    assert result["status"] == "FAIL_LIQUIDITY"
    assert result["eligible"] is False


def test_fill_cap_records_partial_and_unfilled_quantity_without_overfill():
    partial = cap_pilot_fill(10_000, price_rupees=100, traded_value_rupees=1_000_000)
    assert partial["filled_quantity"] == 200
    assert partial["unfilled_quantity"] == 9_800
    assert partial["actual_participation_fraction"] == pytest.approx(PILOT_MAX_PARTICIPATION)
    assert partial["status"] == "PARTIAL"
    unfilled = cap_pilot_fill(10, price_rupees=100, traded_value_rupees=100)
    assert unfilled["filled_quantity"] == 0
    assert unfilled["unfilled_quantity"] == 10
    assert unfilled["status"] == "UNFILLED"


def test_fill_cap_rejects_participation_above_protocol_limit():
    with pytest.raises(ValueError, match="2%"):
        cap_pilot_fill(100, price_rupees=10, traded_value_rupees=100_000,
                       max_participation_fraction=0.03)


def test_timezone_aware_liquidity_dates_are_normalized_to_nse_calendar():
    dates = pd.bdate_range("2026-01-01", periods=21)
    frame = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%dT18:30:00+00:00") for d in dates],
        "traded_value_rupees": [60_000_000.0] * 21,
    })
    # 18:30 UTC is 00:00 on the following NSE calendar date.
    result = assess_pilot_liquidity(
        frame, as_of=pd.Timestamp("2026-01-30T00:00:00+05:30")
    )
    assert result["status"] == "PASS"
    assert result["window_end"] == "2026-01-30"


def test_pilot_execution_constants_match_registered_protocol():
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "config" / "nifty50_pilot_protocol.json").read_text())
    execution = protocol["execution"]
    assert execution["liquidity_filter"]["metric"] == "20_session_median_traded_value"
    assert execution["liquidity_filter"]["minimum_inr"] == 50_000_000
    assert execution["max_order_participation_adv"] == PILOT_MAX_PARTICIPATION
    assert execution["reference_label_participation_adv"] == 0.01
    assert execution["slippage_bps_per_side"] == "15 + 25 * sqrt(participation_fraction / 0.01)"
    assert execution["slippage_at_reference_participation_bps_per_side"] == 40
    assert execution["stress_multiplier"] == 1.5
