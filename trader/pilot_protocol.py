from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PROTOCOL_PATH = Path(__file__).resolve().parents[1] / "config" / "nifty50_pilot_protocol.json"


class PilotProtocolError(ValueError):
    """Raised when the Nifty 50 pilot contract violates a safety invariant."""


def validate_pilot_protocol(protocol: dict[str, Any]) -> list[str]:
    """Validate safety-critical pilot invariants without optional dependencies."""
    errors: list[str] = []
    if protocol.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if protocol.get("experiment_id") != "NIFTY50_PILOT_001":
        errors.append("unexpected experiment_id")
    if protocol.get("status") not in {"DRAFT_NOT_FROZEN", "FROZEN"}:
        errors.append("invalid protocol status")

    registration = protocol.get("registration", {})
    if registration.get("baseline_branch") != "main":
        errors.append("baseline_branch must be main")
    if registration.get("evaluation_authorized") is not False:
        errors.append("evaluation must remain unauthorized")
    if registration.get("holdout_access_authorized") is not False:
        errors.append("holdout access must remain unauthorized")

    universe = protocol.get("universe", {})
    for key, expected in {
        "index": "NIFTY_50",
        "membership": "point_in_time_constituents",
        "selection_count": 5,
        "selection_fraction_at_full_universe": 0.10,
        "expansion_allowed": False,
        "benchmark": "NIFTY_50_TRI",
    }.items():
        if universe.get(key) != expected:
            errors.append(f"universe.{key} must equal {expected!r}")

    target = protocol.get("target", {})
    if target.get("holding_period_trading_sessions") != 5:
        errors.append("target horizon must be five sessions")
    if target.get("positive_class_rule") != "net_relative_excess_return_strictly_greater_than_0.01":
        errors.append("target must use strict >1% net benchmark-relative excess")
    if target.get("reference_costs_independent_of_portfolio_capital") is not True:
        errors.append("label reference costs must not depend on portfolio capital")

    power = protocol.get("statistical_power", {})
    if power.get("maximum_permitted_mde_absolute") != 0.06:
        errors.append("MDE ceiling must remain 6 percentage points")
    if power.get("automatic_decision_if_mde_exceeds_ceiling") != "INCONCLUSIVE":
        errors.append("MDE breach must force INCONCLUSIVE")

    inference = protocol.get("inference", {})
    if inference.get("newey_west_daily_lags") != 10 or inference.get("bootstrap_block_sessions") != 20:
        errors.append("primary inference must use Newey-West 10 lags and 20-session blocks")

    gates = protocol.get("evaluation_gates", [])
    if len(gates) != 16 or [g.get("id") for g in gates] != list(range(1, 17)):
        errors.append("exactly 16 ordered evaluation gates are required")

    outcomes = protocol.get("outcomes", {})
    for key in (
        "pilot_go_authorizes_promotion",
        "pilot_go_authorizes_paper_trading",
        "pilot_go_authorizes_live_trading",
    ):
        if outcomes.get(key) is not False:
            errors.append(f"outcomes.{key} must remain false")

    safety = protocol.get("safety", {})
    for key in ("promotion_eligible", "paper_trading_eligible", "live_execution_enabled", "model_evaluation_authorized"):
        if safety.get(key) is not False:
            errors.append(f"safety.{key} must remain false")

    if protocol.get("status") == "FROZEN" and protocol.get("unresolved_freeze_items"):
        errors.append("a frozen protocol cannot contain unresolved freeze items")
    return errors


def load_pilot_protocol(path: Path = DEFAULT_PROTOCOL_PATH) -> dict[str, Any]:
    """Load and validate the registered pilot protocol."""
    try:
        protocol = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotProtocolError(f"cannot load pilot protocol: {exc}") from exc
    errors = validate_pilot_protocol(protocol)
    if errors:
        raise PilotProtocolError("; ".join(errors))
    return protocol


def main() -> int:
    protocol = load_pilot_protocol()
    print(
        f"{protocol['experiment_id']}: {protocol['status']} "
        f"(evaluation_authorized={protocol['registration']['evaluation_authorized']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
