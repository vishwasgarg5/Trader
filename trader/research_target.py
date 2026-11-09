"""Validated adapter for the registered Nifty 50 pilot target contract."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL_PATH = ROOT / "config" / "nifty50_pilot_protocol.json"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class ResearchTarget:
    holding_period_sessions: int
    benchmark: str
    positive_excess_threshold: float
    equality_label: int
    selection_count: int
    cost_profile_id: str
    protocol_status: str
    evaluation_authorized: bool
    holdout_access_authorized: bool


def load_target_contract(path: str | Path = DEFAULT_PROTOCOL_PATH) -> ResearchTarget:
    """Load and enforce the small, immutable set of target-defining protocol fields."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
        protocol = json.loads(raw, object_pairs_hook=_unique_object,
                              parse_constant=lambda value: (_ for _ in ()).throw(
                                  ValueError(f"invalid JSON numeric constant: {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load pilot protocol: {exc}") from exc
    if not isinstance(protocol, dict):
        raise ValueError("pilot protocol must be a JSON object")
    try:
        target = protocol["target"]
        universe = protocol["universe"]
        registration = protocol["registration"]
        execution = protocol["execution"]
        status = protocol["status"]
        holding = target["holding_period_trading_sessions"]
        benchmark = universe["benchmark"]
        rule = target["positive_class_rule"]
        equality = target["equality_at_threshold_label"]
        formula = target["formula"]
        invalid = target["invalid_or_unavailable_outcome"]
        selection = universe["selection_count"]
        cost_id = target["reference_cost_profile_id"]
        evaluation = registration["evaluation_authorized"]
        holdout = registration["holdout_access_authorized"]
        cost_status = execution["status"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"pilot protocol is missing required target fields: {exc}") from exc

    expected = {
        "holding_period_trading_sessions": (holding, 5),
        "benchmark": (benchmark, "NIFTY_50_TRI"),
        "positive_class_rule": (rule, "net_relative_excess_return_strictly_greater_than_0.01"),
        "equality_at_threshold_label": (equality, 0),
        "formula": (formula, "net_stock_total_return_after_fixed_reference_costs_minus_matched_NIFTY_50_TRI_return"),
        "invalid_or_unavailable_outcome": (invalid, "UNRESOLVED_EXCLUDED_NOT_NEGATIVE"),
        "selection_count": (selection, 5),
    }
    for name, (actual, required) in expected.items():
        if type(actual) is not type(required) or actual != required:
            raise ValueError(f"pilot protocol contract mismatch for {name}: expected {required!r}")
    if not isinstance(cost_id, str) or not cost_id.strip():
        raise ValueError("reference_cost_profile_id must be a non-empty string")
    if not isinstance(status, str) or not isinstance(cost_status, str):
        raise ValueError("protocol and execution statuses must be strings")
    if type(evaluation) is not bool or type(holdout) is not bool:
        raise ValueError("evaluation and holdout authorizations must be booleans")
    if evaluation or holdout:
        raise ValueError("protocol adapter cannot authorize evaluation or holdout access")
    return ResearchTarget(
        holding_period_sessions=holding,
        benchmark=benchmark,
        positive_excess_threshold=0.01,
        equality_label=equality,
        selection_count=selection,
        cost_profile_id=cost_id,
        protocol_status=status,
        evaluation_authorized=evaluation,
        holdout_access_authorized=holdout,
    )
