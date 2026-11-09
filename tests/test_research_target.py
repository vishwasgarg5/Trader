import json

import pytest

from trader.research_target import load_target_contract


def protocol():
    return {
        "status": "DRAFT_NOT_FROZEN",
        "registration": {"evaluation_authorized": False, "holdout_access_authorized": False},
        "universe": {"benchmark": "NIFTY_50_TRI", "selection_count": 5},
        "target": {
            "holding_period_trading_sessions": 5,
            "positive_class_rule": "net_relative_excess_return_strictly_greater_than_0.01",
            "equality_at_threshold_label": 0,
            "formula": "net_stock_total_return_after_fixed_reference_costs_minus_matched_NIFTY_50_TRI_return",
            "invalid_or_unavailable_outcome": "UNRESOLVED_EXCLUDED_NOT_NEGATIVE",
            "reference_cost_profile_id": "NIFTY50_PILOT_LABEL_COST_V1",
        },
        "execution": {"status": "PROPOSED_PENDING_BROKER_TARIFF_VALIDATION"},
    }


def test_loads_registered_target_without_unlocking_gates(tmp_path):
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol()))
    contract = load_target_contract(path)
    assert contract.holding_period_sessions == 5
    assert contract.benchmark == "NIFTY_50_TRI"
    assert contract.positive_excess_threshold == 0.01
    assert contract.equality_label == 0
    assert contract.selection_count == 5
    assert contract.evaluation_authorized is False
    assert contract.holdout_access_authorized is False


@pytest.mark.parametrize("path_change", [
    ("target", "holding_period_trading_sessions", 4),
    ("universe", "benchmark", "NIFTY_50"),
    ("target", "positive_class_rule", "net_relative_excess_return_greater_than_or_equal_to_0.01"),
    ("universe", "selection_count", 4),
])
def test_rejects_contract_drift(tmp_path, path_change):
    data = protocol()
    section, key, value = path_change
    data[section][key] = value
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="contract mismatch"):
        load_target_contract(path)


def test_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "protocol.json"
    path.write_text('{"status":"DRAFT","status":"FROZEN"}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_target_contract(path)


def test_never_accepts_authorization_flags(tmp_path):
    data = protocol()
    data["registration"]["evaluation_authorized"] = True
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cannot authorize"):
        load_target_contract(path)
