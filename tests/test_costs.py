import pytest

from trader.costs import DEFAULT_DELIVERY_COSTS, delivery_round_trip_cost


def test_delivery_costs_include_both_side_stt_and_buy_stamp_duty():
    result = delivery_round_trip_cost(100, 100, slippage_bps_per_side=0)
    assert result["stt_rupees"] == pytest.approx(200.0)
    assert result["stamp_duty_rupees"] == pytest.approx(15.0)
    assert result["exchange_rupees"] == pytest.approx(6.1398)
    assert result["ipft_rupees"] == pytest.approx(0.0002)
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


@pytest.mark.parametrize("parameter", [
    "stt_rate_each_side", "gst_rate", "brokerage_cap_per_order",
    "dp_charge_per_sell", "slippage_bps_per_side",
])
@pytest.mark.parametrize("invalid", [float("nan"), float("inf")])
def test_cost_api_rejects_non_finite_parameters(parameter, invalid):
    with pytest.raises(ValueError, match="must be finite"):
        delivery_round_trip_cost(100, 100, **{parameter: invalid})


def test_contract_note_reconciliation_matches_modeled_charge_components():
    import pandas as pd
    from trader.costs import reconcile_groww_contract_notes

    estimate = delivery_round_trip_cost(
        100, 105, notional_rupees=10000, slippage_bps_per_side=0,
    )
    observation = {
        "entry_price": 100,
        "exit_price": 105,
        "notional_rupees": 10000,
        "actual_brokerage_rupees": estimate["brokerage_rupees"],
        "actual_stt_rupees": estimate["stt_rupees"],
        "actual_stamp_duty_rupees": estimate["stamp_duty_rupees"],
        "actual_exchange_rupees": estimate["exchange_rupees"],
        "actual_ipft_rupees": estimate["ipft_rupees"],
        "actual_sebi_rupees": estimate["sebi_rupees"],
        "actual_dp_rupees": estimate["dp_rupees"],
        "actual_gst_rupees": estimate["gst_rupees"],
    }
    result = reconcile_groww_contract_notes(pd.DataFrame([observation]))
    assert bool(result.iloc[0]["within_tolerance"]) is True
    assert result.iloc[0]["total_delta_rupees"] == pytest.approx(0.0)


def test_contract_note_reconciliation_flags_component_mismatch():
    import pandas as pd
    from trader.costs import reconcile_groww_contract_notes

    estimate = delivery_round_trip_cost(
        100, 100, notional_rupees=10000, slippage_bps_per_side=0,
    )
    observation = {
        "entry_price": 100,
        "exit_price": 100,
        "notional_rupees": 10000,
        "actual_brokerage_rupees": estimate["brokerage_rupees"],
        "actual_stt_rupees": estimate["stt_rupees"],
        "actual_stamp_duty_rupees": estimate["stamp_duty_rupees"],
        "actual_exchange_rupees": estimate["exchange_rupees"],
        "actual_ipft_rupees": estimate["ipft_rupees"],
        "actual_sebi_rupees": estimate["sebi_rupees"],
        "actual_dp_rupees": estimate["dp_rupees"] + 1,
        "actual_gst_rupees": estimate["gst_rupees"],
    }
    result = reconcile_groww_contract_notes(pd.DataFrame([observation]))
    assert bool(result.iloc[0]["within_tolerance"]) is False
    assert result.iloc[0]["delta_dp_rupees"] == pytest.approx(1.0)


def test_contract_note_reconciliation_requires_all_fee_components():
    import pandas as pd
    from trader.costs import reconcile_groww_contract_notes

    with pytest.raises(ValueError, match="missing columns"):
        reconcile_groww_contract_notes(pd.DataFrame([{"entry_price": 100}]))
