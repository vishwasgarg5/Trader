import pytest

from trader.costs import DEFAULT_DELIVERY_COSTS, delivery_round_trip_cost


def test_delivery_costs_include_both_side_stt_and_buy_stamp_duty():
    result = delivery_round_trip_cost(100, 100, slippage_bps_per_side=0)
    assert result["stt_rupees"] == pytest.approx(200.0)
    assert result["stamp_duty_rupees"] == pytest.approx(15.0)
    assert result["exchange_rupees"] == pytest.approx(5.94)
    assert result["ipft_rupees"] == pytest.approx(0.2)
    assert result["sebi_rupees"] == pytest.approx(0.2)
    assert result["net_return"] < 0
    assert result["cost_return"] > 0.002


def test_brokerage_cap_is_applied_per_side():
    result = delivery_round_trip_cost(
        100, 100, brokerage_rate_each_side=0.01, brokerage_cap_per_order=20,
        slippage_bps_per_side=0,
    )
    assert result["brokerage_rupees"] == pytest.approx(40.0)


def test_default_cost_assumptions_are_explicit_and_parameterized():
    assert DEFAULT_DELIVERY_COSTS["stt_rate_each_side"] == pytest.approx(0.001)
    assert DEFAULT_DELIVERY_COSTS["slippage_bps_per_side"] == 2.0



def test_groww_delivery_defaults_include_brokerage_and_dp_charges():
    result = delivery_round_trip_cost(
        100, 100, notional_rupees=10000, slippage_bps_per_side=0,
    )
    # ₹10 brokerage per side (0.1% of ₹10,000), plus ₹20 DP on sell.
    assert result["brokerage_rupees"] == pytest.approx(20.0)
    assert result["dp_rupees"] == pytest.approx(20.0)
    assert result["gst_rupees"] > 0


def test_groww_minimum_brokerage_and_small_sell_dp_exemption():
    result = delivery_round_trip_cost(
        100, 100, notional_rupees=1000, slippage_bps_per_side=0,
    )
    assert result["brokerage_rupees"] == pytest.approx(10.0)
    small = delivery_round_trip_cost(
        100, 100, **{**DEFAULT_DELIVERY_COSTS, "notional_rupees": 50,
                    "slippage_bps_per_side": 0},
    )
    # Groww's ₹16.50 component is waived below ₹100; the ₹3.50
    # depository component remains payable (before GST).
    assert small["dp_rupees"] == pytest.approx(3.5)
    assert small["brokerage_rupees"] == pytest.approx(2.5)


def test_default_cost_api_retains_depository_fee_below_100_rupees():
    small = delivery_round_trip_cost(
        100, 100, notional_rupees=50, slippage_bps_per_side=0,
    )
    assert small["dp_rupees"] == pytest.approx(3.5)


def test_groww_dp_threshold_waives_only_groww_component():
    small = delivery_round_trip_cost(
        100, 100, **{**DEFAULT_DELIVERY_COSTS, "notional_rupees": 99.99,
                    "slippage_bps_per_side": 0},
    )
    regular = delivery_round_trip_cost(
        100, 100, **{**DEFAULT_DELIVERY_COSTS, "notional_rupees": 100.0,
                    "slippage_bps_per_side": 0},
    )
    assert small["dp_rupees"] == pytest.approx(3.5)
    assert regular["dp_rupees"] == pytest.approx(20.0)
