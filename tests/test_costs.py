import pytest

from trader.costs import DEFAULT_DELIVERY_COSTS, delivery_round_trip_cost


def test_delivery_costs_include_both_side_stt_and_buy_stamp_duty():
    result = delivery_round_trip_cost(100, 100, slippage_bps_per_side=0)
    assert result["stt_rupees"] == pytest.approx(200.0)
    assert result["stamp_duty_rupees"] == pytest.approx(15.0)
    assert result["exchange_rupees"] == pytest.approx(6.14)
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
