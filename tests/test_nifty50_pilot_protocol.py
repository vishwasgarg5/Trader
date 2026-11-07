import copy
import json
from pathlib import Path

import pytest

from trader.pilot_protocol import (
    PilotProtocolError,
    load_pilot_protocol,
    validate_pilot_protocol,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "nifty50_pilot_protocol.json"


def test_registered_protocol_loads_and_is_not_frozen():
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    assert protocol["status"] == "DRAFT_NOT_FROZEN"
    assert protocol["registration"]["evaluation_authorized"] is False


def test_protocol_is_nifty50_only_with_exactly_five_selections():
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    assert protocol["universe"]["index"] == "NIFTY_50"
    assert protocol["universe"]["selection_count"] == 5
    assert protocol["universe"]["expansion_allowed"] is False


def test_pilot_go_cannot_authorize_promotion_or_trading():
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    assert protocol["outcomes"]["pilot_go_authorizes_promotion"] is False
    assert protocol["outcomes"]["pilot_go_authorizes_paper_trading"] is False
    assert protocol["outcomes"]["pilot_go_authorizes_live_trading"] is False


def test_promotion_and_live_execution_remain_disabled():
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    assert protocol["safety"]["promotion_eligible"] is False
    assert protocol["safety"]["paper_trading_eligible"] is False
    assert protocol["safety"]["live_execution_enabled"] is False


def test_fixed_horizon_target_and_cost_reference_are_registered():
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    assert protocol["target"]["holding_period_trading_sessions"] == 5
    assert protocol["target"]["positive_class_rule"].endswith("greater_than_0.01")
    assert protocol["target"]["reference_costs_independent_of_portfolio_capital"] is True


def test_power_ceiling_and_inference_settings_are_registered():
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    assert protocol["statistical_power"]["maximum_permitted_mde_absolute"] == 0.06
    assert protocol["inference"]["newey_west_daily_lags"] == 10
    assert protocol["inference"]["bootstrap_block_sessions"] == 20


def test_exactly_sixteen_ordered_gates_are_registered():
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    assert [gate["id"] for gate in protocol["evaluation_gates"]] == list(range(1, 17))


@pytest.mark.parametrize(
    ("mutate", "expected_fragment"),
    [
        (lambda p: p["universe"].update(index="NIFTY_500"), "universe.index"),
        (lambda p: p["universe"].update(selection_count=10), "selection_count"),
        (lambda p: p["statistical_power"].update(maximum_permitted_mde_absolute=0.08), "MDE ceiling"),
        (lambda p: p["registration"].update(evaluation_authorized=True), "evaluation must remain unauthorized"),
        (lambda p: p["safety"].update(live_execution_enabled=True), "live_execution_enabled"),
        (lambda p: p["outcomes"].update(pilot_go_authorizes_paper_trading=True), "pilot_go_authorizes_paper_trading"),
        (lambda p: p.update(status="FROZEN"), "frozen protocol cannot contain unresolved"),
    ],
)
def test_safety_invariant_mutations_are_rejected(mutate, expected_fragment):
    protocol = load_pilot_protocol(PROTOCOL_PATH)
    mutated = copy.deepcopy(protocol)
    mutate(mutated)
    assert any(expected_fragment in error for error in validate_pilot_protocol(mutated))


def test_loader_rejects_invalid_protocol(tmp_path):
    invalid = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    invalid["universe"]["expansion_allowed"] = True
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(PilotProtocolError):
        load_pilot_protocol(path)
