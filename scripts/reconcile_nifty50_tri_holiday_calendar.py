#!/usr/bin/env python3
"""Cross-check NSE holiday candidates against acquired NIFTY 50 TRI dates.

Diagnostic only: annual circular extraction and TRI observations are not yet
independently authenticated. This report must never certify calendar coverage.
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

TRI_CSV = Path("data/reference/nifty50_tri.csv")
HOLIDAY_REPORT = Path("data/reports/nifty50_tri_holiday_extraction.json")
WEEKEND_REGISTER = Path("data/reference/nifty50_tri_weekend_session_review.csv")
GAP_AUDIT = Path("data/reports/nifty50_tri_calendar_audit.json")
OUTPUT = Path("data/reports/nifty50_tri_holiday_reconciliation.json")


def load_dates() -> tuple[list[date], set[date]]:
    with TRI_CSV.open(newline="", encoding="utf-8") as handle:
        sessions = [date.fromisoformat(row["session_date"]) for row in csv.DictReader(handle)]
    if sessions != sorted(set(sessions)):
        raise ValueError("TRI session dates must be unique and chronological")
    with WEEKEND_REGISTER.open(newline="", encoding="utf-8") as handle:
        weekend_sessions = {
            date.fromisoformat(row["session_date"]) for row in csv.DictReader(handle)
        }
    return sessions, weekend_sessions


def main() -> int:
    sessions, weekend_sessions = load_dates()
    session_set = set(sessions)
    extracted = json.loads(HOLIDAY_REPORT.read_text(encoding="utf-8"))
    gap_audit = json.loads(GAP_AUDIT.read_text(encoding="utf-8"))
    holiday_rows = [
        row
        for record in extracted.get("records", [])
        for row in record.get("candidate_dates", [])
    ]
    holiday_dates = {date.fromisoformat(row["date"]) for row in holiday_rows}

    holiday_checks = []
    for row in holiday_rows:
        day = date.fromisoformat(row["date"])
        holiday_checks.append({
            **row,
            "tri_observation_present": day in session_set,
            "calendar_day_type": "WEEKEND" if day.weekday() >= 5 else "WEEKDAY",
            "weekend_session_register_match": day in weekend_sessions,
            "interpretation": (
                "TRI_OBSERVATION_ON_CIRCULAR_HOLIDAY_REVIEW_SESSION_TYPE"
                if day in session_set
                else "NO_TRI_OBSERVATION_ON_CIRCULAR_HOLIDAY_EXPECTED_CLOSED"
            ),
        })

    gap_checks = []
    for gap in gap_audit.get("gaps_over_three_calendar_days", []):
        previous = date.fromisoformat(gap["previous_session"])
        following = date.fromisoformat(gap["next_session"])
        intervening = [
            previous + timedelta(days=offset)
            for offset in range(1, (following - previous).days)
        ]
        weekend_days = [day for day in intervening if day.weekday() >= 5]
        circular_holidays = [day for day in intervening if day in holiday_dates]
        unexplained_weekdays = [
            day for day in intervening
            if day.weekday() < 5 and day not in holiday_dates
        ]
        gap_checks.append({
            "previous_session": previous.isoformat(),
            "next_session": following.isoformat(),
            "calendar_days_between": (following - previous).days,
            "intervening_dates": [day.isoformat() for day in intervening],
            "weekend_dates": [day.isoformat() for day in weekend_days],
            "annual_circular_holiday_dates": [day.isoformat() for day in circular_holidays],
            "unexplained_weekday_dates": [day.isoformat() for day in unexplained_weekdays],
            "status": (
                "NO_UNEXPLAINED_WEEKDAY_IN_GAP"
                if not unexplained_weekdays else "UNRESOLVED_WEEKDAY_GAP"
            ),
        })

    counts = {
        "candidate_holiday_rows": len(holiday_rows),
        "distinct_candidate_holiday_dates": len(holiday_dates),
        "candidate_holiday_dates_present_in_tri": sum(
            day in session_set for day in holiday_dates
        ),
        "candidate_holiday_dates_absent_from_tri": sum(
            day not in session_set for day in holiday_dates
        ),
        "holiday_weekday_mismatch_flags": sum(
            row.get("weekday_matches_date") is False for row in holiday_rows
        ),
        "holiday_rows_missing_source_weekday": sum(
            row.get("weekday_in_source") is None for row in holiday_rows
        ),
        "gaps_over_three_calendar_days": len(gap_checks),
        "gaps_without_unexplained_weekdays": sum(
            row["status"] == "NO_UNEXPLAINED_WEEKDAY_IN_GAP" for row in gap_checks
        ),
        "gaps_with_unexplained_weekdays": sum(
            row["status"] == "UNRESOLVED_WEEKDAY_GAP" for row in gap_checks
        ),
        "distinct_unexplained_weekday_dates": len({
            day for gap in gap_checks for day in gap["unexplained_weekday_dates"]
        }),
        "weekend_session_register_dates_present_in_tri": sum(
            day in session_set for day in weekend_sessions
        ),
        "weekend_session_register_date_count": len(weekend_sessions),
    }
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "audit_type": "HOLIDAY_CIRCULAR_TO_TRI_DIAGNOSTIC_CROSSCHECK",
        "tri_source": TRI_CSV.as_posix(),
        "holiday_extraction_source": HOLIDAY_REPORT.as_posix(),
        "weekend_session_register_source": WEEKEND_REGISTER.as_posix(),
        "counts": counts,
        "holiday_date_checks": holiday_checks,
        "gap_checks": gap_checks,
        "interpretation": (
            "This is a diagnostic comparison only. A circular holiday absent from TRI "
            "is consistent with a closure but does not prove the entire calendar is complete. "
            "A TRI observation on a circular holiday requires session-type review. "
            "Unexplained weekdays may be missing data, ad-hoc closures, or other exchange "
            "events and must not be auto-classified."
        ),
        "calendar_completeness": "NOT_CERTIFIED",
        "source_authenticity": "PENDING_INDEPENDENT_REVIEW",
        "independent_review_status": "PENDING",
        "research_status": "RESEARCH_HOLD",
        "holdout_access_authorized": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": counts, "calendar_completeness": "NOT_CERTIFIED"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
