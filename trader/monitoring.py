"""Fail-closed operational and research monitoring for daily Trader outputs.

This monitor reports data-integrity blockers separately from operational errors.
It never changes promotion status, unlocks the final holdout, or enables orders.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data" / "reports" / "monitoring.json"
INPUTS = (
    ROOT / "data" / "reports" / "data_integrity.json",
    ROOT / "data" / "reports" / "metrics.json",
    ROOT / "data" / "signals" / "latest_signals.csv",
    ROOT / "data" / "logs" / "predictions.csv",
    ROOT / "config" / "promotion_gate.json",
)


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_monitoring_report(root: Path = ROOT, generated_at: datetime | None = None) -> dict:
    root = Path(root)
    integrity_path = root / "data/reports/data_integrity.json"
    metrics_path = root / "data/reports/metrics.json"
    signals_path = root / "data/signals/latest_signals.csv"
    predictions_path = root / "data/logs/predictions.csv"
    gate_path = root / "config/promotion_gate.json"
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, dict] = {}

    loaded: dict[str, dict] = {}
    for name, path in (
        ("data_integrity", integrity_path), ("metrics", metrics_path),
        ("promotion_gate", gate_path),
    ):
        try:
            loaded[name] = _read_json(path)
            checks[f"{name}_readable"] = {"passed": True}
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{name} report unavailable or invalid: {exc}")
            checks[f"{name}_readable"] = {"passed": False, "detail": str(exc)}

    integrity = loaded.get("data_integrity", {})
    metrics = loaded.get("metrics", {})
    gate = loaded.get("promotion_gate", {})

    price_passed = integrity.get("price_validation", {}).get("passed") is True
    checks["configured_price_validation"] = {"passed": price_passed}
    if not price_passed:
        warnings.append("Configured-symbol price validation has not passed.")

    membership = integrity.get("universe_audit", {}).get("membership_history", {})
    membership_passed = membership.get("point_in_time_verified") is True
    checks["point_in_time_membership"] = {
        "passed": membership_passed, "rows": membership.get("rows", 0),
    }
    if not membership_passed:
        warnings.append("Point-in-time Nifty 50 membership is not independently verified.")

    corporate = integrity.get("corporate_action_audit", {})
    corporate_passed = corporate.get("corporate_action_adjustment_verified") is True
    checks["corporate_action_lineage"] = {
        "passed": corporate_passed,
        "unresolved_rows": corporate.get("unresolved_adjustment_factor_rows"),
    }
    if not corporate_passed:
        warnings.append("Corporate-action adjusted-price lineage is not independently verified.")

    if gate:
        gate_safe = (
            gate.get("status") != "APPROVED"
            or (gate.get("promotion_eligible") is False and gate.get("live_execution_enabled") is False)
        )
        checks["promotion_gate_fail_closed"] = {"passed": gate_safe, "status": gate.get("status")}
        if not gate_safe:
            errors.append("Promotion gate is APPROVED without both explicit promotion and live-execution controls being false.")
    else:
        checks["promotion_gate_fail_closed"] = {"passed": False}
    if integrity and (
        integrity.get("promotion_eligible") is not False
        or integrity.get("live_execution_enabled") is not False
    ):
        errors.append("Data-integrity report does not explicitly keep promotion and live execution disabled.")

    latest_date = None
    signal_rows: list[dict] = []
    try:
        signal_rows = _read_csv(signals_path)
        required = {"as_of", "symbol", "signal", "prob_up_5d", "promotion_eligible"}
        missing = required.difference(signal_rows[0].keys() if signal_rows else [])
        if not signal_rows or missing:
            raise ValueError(f"empty signals or missing columns: {sorted(missing)}")
        dates = []
        for row in signal_rows:
            dates.append(datetime.strptime(row["as_of"], "%Y-%m-%d").date())
            probability = float(row["prob_up_5d"])
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError(f"invalid probability for {row['symbol']}")
            if row["promotion_eligible"].strip().lower() != "false":
                raise ValueError(f"signal for {row['symbol']} is not explicitly research-only")
            if not row["signal"].startswith("RESEARCH_ONLY_"):
                raise ValueError(f"signal for {row['symbol']} lacks RESEARCH_ONLY_ prefix")
        latest_date = max(dates).isoformat()
        checks["latest_signals_valid"] = {"passed": True, "rows": len(signal_rows), "as_of": latest_date}
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"Latest signal validation failed: {exc}")
        checks["latest_signals_valid"] = {"passed": False, "detail": str(exc)}

    symbol_dates = [
        details.get("last_date")
        for details in integrity.get("universe_audit", {}).get("per_symbol", {}).values()
        if details.get("last_date")
    ]
    latest_price_date = max(symbol_dates) if symbol_dates else None
    dates_match = bool(latest_date and latest_price_date and latest_date == latest_price_date)
    checks["signal_price_date_alignment"] = {
        "passed": dates_match, "signal_date": latest_date, "latest_price_date": latest_price_date,
    }
    if latest_date and latest_price_date and not dates_match:
        warnings.append("Latest signal date does not match the latest configured-symbol price date.")
    elif not latest_price_date:
        warnings.append("Price freshness cannot be assessed from the integrity report.")

    # Probability-shift monitoring needs 40 distinct sessions; with less history
    # the monitor explicitly reports insufficient evidence rather than a false pass.
    try:
        prediction_rows = _read_csv(predictions_path)
        by_date: dict[str, list[float]] = {}
        for row in prediction_rows:
            date = row.get("as_of", "")
            value = float(row.get("prob_up_5d", "nan"))
            if date and math.isfinite(value) and 0 <= value <= 1:
                by_date.setdefault(date, []).append(value)
        session_means = [
            (date, sum(values) / len(values))
            for date, values in sorted(by_date.items())
        ]
        if len(session_means) >= 40:
            prior = [v for _, v in session_means[-40:-20]]
            recent = [v for _, v in session_means[-20:]]
            shift = sum(recent) / len(recent) - sum(prior) / len(prior)
            drift_passed = abs(shift) <= 0.10
            checks["prediction_probability_drift"] = {
                "status": "CHECKED", "passed": drift_passed,
                "sessions": len(session_means), "mean_shift_recent20_vs_prior20": shift,
                "threshold_absolute": 0.10,
            }
            if not drift_passed:
                warnings.append("Prediction probability mean shifted by more than 0.10 versus the prior 20 sessions.")
        else:
            checks["prediction_probability_drift"] = {
                "status": "INSUFFICIENT_HISTORY", "sessions": len(session_means),
                "sessions_required": 40,
            }
            warnings.append("Prediction drift is not yet statistically monitored: 40 distinct sessions are required.")
    except (OSError, ValueError) as exc:
        errors.append(f"Prediction drift input is unavailable or invalid: {exc}")
        checks["prediction_probability_drift"] = {"status": "ERROR", "detail": str(exc)}

    accuracy = metrics.get("accuracy")
    baseline = metrics.get("baseline_accuracy_majority")
    if accuracy is not None and baseline is not None:
        comparison_passed = float(accuracy) > float(baseline)
        checks["accuracy_vs_majority_baseline"] = {
            "passed": comparison_passed, "accuracy": accuracy, "baseline": baseline,
        }
        if not comparison_passed:
            warnings.append("Classifier accuracy does not exceed the majority-class baseline.")
    else:
        checks["accuracy_vs_majority_baseline"] = {"status": "UNAVAILABLE"}

    manifest = {}
    for path in (integrity_path, metrics_path, signals_path, predictions_path, gate_path):
        manifest[str(path.relative_to(root))] = _sha256(path)
    generated_at = generated_at or datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "generated_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "code_revision": os.environ.get("GITHUB_SHA", "local_or_unavailable"),
        "status": "ALERT" if errors else "RESEARCH_HOLD" if warnings else "HEALTHY",
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "input_sha256": manifest,
        "promotion_eligible": False,
        "live_execution_enabled": False,
        "policy": "Monitoring is diagnostic only; it never authorizes promotion, holdout access, or live execution.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = build_monitoring_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "errors": report["errors"],
        "warnings": report["warnings"],
        "output": str(args.output),
    }, indent=2))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
