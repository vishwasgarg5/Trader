import csv
import json
from datetime import datetime, timezone

from trader.monitoring import build_monitoring_report


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _monitor_root(tmp_path):
    _write_json(tmp_path / "data/reports/data_integrity.json", {
        "price_validation": {"passed": True},
        "universe_audit": {
            "membership_history": {"point_in_time_verified": False, "rows": 0},
            "per_symbol": {"ABC.NS": {"last_date": "2026-11-06"}},
        },
        "corporate_action_audit": {
            "corporate_action_adjustment_verified": False,
            "unresolved_adjustment_factor_rows": 2,
        },
        "promotion_eligible": False,
        "live_execution_enabled": False,
    })
    _write_json(tmp_path / "data/reports/metrics.json", {
        "accuracy": 0.61, "baseline_accuracy_majority": 0.63,
    })
    _write_json(tmp_path / "config/promotion_gate.json", {
        "status": "RESEARCH_HOLD", "promotion_eligible": False,
        "live_execution_enabled": False,
    })
    _write_csv(tmp_path / "data/signals/latest_signals.csv",
               ["as_of", "symbol", "signal", "prob_up_5d", "promotion_eligible"],
               [{"as_of": "2026-11-06", "symbol": "ABC.NS",
                 "signal": "RESEARCH_ONLY_HOLD", "prob_up_5d": "0.55",
                 "promotion_eligible": "False"}])
    _write_csv(tmp_path / "data/logs/predictions.csv",
               ["as_of", "prob_up_5d"],
               [{"as_of": "2026-11-06", "prob_up_5d": "0.55"}])


def test_monitor_reports_research_hold_without_promoting_incomplete_evidence(tmp_path):
    _monitor_root(tmp_path)
    report = build_monitoring_report(
        tmp_path, datetime(2026, 11, 6, tzinfo=timezone.utc)
    )
    assert report["status"] == "RESEARCH_HOLD"
    assert report["promotion_eligible"] is False
    assert report["live_execution_enabled"] is False
    assert report["checks"]["point_in_time_membership"]["passed"] is False
    assert report["checks"]["prediction_probability_drift"]["status"] == "INSUFFICIENT_HISTORY"
    assert any("majority-class baseline" in warning for warning in report["warnings"])


def test_monitor_detects_signal_that_is_not_research_only(tmp_path):
    _monitor_root(tmp_path)
    _write_csv(tmp_path / "data/signals/latest_signals.csv",
               ["as_of", "symbol", "signal", "prob_up_5d", "promotion_eligible"],
               [{"as_of": "2026-11-06", "symbol": "ABC.NS", "signal": "BUY",
                 "prob_up_5d": "0.8", "promotion_eligible": "True"}])
    report = build_monitoring_report(tmp_path)
    assert report["status"] == "ALERT"
    assert any("lacks RESEARCH_ONLY_" in error or "not explicitly research-only" in error
               for error in report["errors"])
