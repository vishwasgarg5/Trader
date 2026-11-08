#!/usr/bin/env python3
"""Cross-check NSE holiday candidates against acquired NIFTY 50 TRI dates.

Diagnostic only: source bytes and dates remain pending independent review.
This report must never certify calendar coverage.\nA pending PDF archive remains explicitly provisional in the report.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

TRI_CSV = Path("data/reference/nifty50_tri.csv")
HOLIDAY_REPORT = Path("data/reports/nifty50_tri_holiday_extraction.json")
WEEKEND_REGISTER = Path("data/reference/nifty50_tri_weekend_session_review.csv")
AD_HOC_REGISTER = Path("data/reference/nifty50_tri_ad_hoc_closures.csv")
AD_HOC_MANIFEST = Path("data/reports/nifty50_tri_ad_hoc_closure_archive.json")
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


def load_ad_hoc_closures() -> list[dict]:
    manifest = json.loads(AD_HOC_MANIFEST.read_text(encoding="utf-8"))
    archived = {row["circular_reference"]: row for row in manifest.get("records", [])}
    failed = {row["circular_reference"]: row for row in manifest.get("failures", [])}
    result = []
    with AD_HOC_REGISTER.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            archived_row = archived.get(row["circular_reference"])
            if archived_row:
                path = Path(archived_row["archive_path"])
                raw = path.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                if digest != archived_row["sha256"]:
                    raise ValueError(f"SHA-256 mismatch for {row['circular_reference']}")
                archive_verified = True
                archive_status = "ARCHIVED_PDF_SIGNATURE_VALID"
                archive_sha256 = digest
            else:
                failure = failed.get(row["circular_reference"])
                if not failure or row["event_type"] != "HOLIDAY_DATE_REVISION":
                    raise ValueError(f"missing archived circular: {row['circular_reference']}")
                archive_verified = False
                archive_status = "SOURCE_IDENTIFIED_PDF_ARCHIVE_PENDING"
                archive_sha256 = None
            result.append({
                **row,
                "session_date": date.fromisoformat(row["session_date"]),
                "supersedes_session_date": (
                    date.fromisoformat(row["supersedes_session_date"])
                    if row["supersedes_session_date"] else None
                ),
                "archive_sha256_verified": archive_sha256,
                "archive_integrity_verified": archive_verified,
                "archive_status": archive_status,
                "independent_review_status": "PENDING",
            })
    if len(result) != manifest.get("expected_count"):
        raise ValueError("ad-hoc register and archive manifest counts do not match")
    if len(archived) + len(failed) != manifest.get("expected_count"):
        raise ValueError("ad-hoc archive manifest does not account for every registered circular")
    return result


def main() -> int:
    sessions, weekend_sessions = load_dates()
    session_set = set(sessions)
    extracted = json.loads(HOLIDAY_REPORT.read_text(encoding="utf-8"))
    gap_audit = json.loads(GAP_AUDIT.read_text(encoding="utf-8"))
    ad_hoc_rows = load_ad_hoc_closures()
    holiday_rows = [
        row
        for record in extracted.get("records", [])
        for row in record.get("candidate_dates", [])
    ]
    holiday_dates = {date.fromisoformat(row["date"]) for row in holiday_rows}
    superseded_dates = {
        row["supersedes_session_date"] for row in ad_hoc_rows
        if row["supersedes_session_date"] is not None
    }
    effective_annual_holiday_dates = holiday_dates - superseded_dates
    ad_hoc_closure_dates = {
        row["session_date"] for row in ad_hoc_rows
        if row["event_type"] == "AD_HOC_CLOSURE"
    }
    revised_holiday_dates = {
        row["session_date"] for row in ad_hoc_rows
        if row["event_type"] == "HOLIDAY_DATE_REVISION"
    }
    effective_closure_dates = (
        effective_annual_holiday_dates | ad_hoc_closure_dates | revised_holiday_dates
    )

    holiday_checks = []
    for row in holiday_rows:
        day = date.fromisoformat(row["date"])
        superseded = day in superseded_dates
        holiday_checks.append({
            **row,
            "tri_observation_present": day in session_set,
            "calendar_day_type": "WEEKEND" if day.weekday() >= 5 else "WEEKDAY",
            "weekend_session_register_match": day in weekend_sessions,
            "superseded_by_later_nse_circular": superseded,
            "interpretation": (
                "ANNUAL_HOLIDAY_DATE_SUPERSEDED_BY_LATER_NSE_CIRCULAR"
                if superseded else (
                    "TRI_OBSERVATION_ON_CIRCULAR_HOLIDAY_REVIEW_SESSION_TYPE"
                    if day in session_set else
                    "NO_TRI_OBSERVATION_ON_CIRCULAR_HOLIDAY_EXPECTED_CLOSED"
                )
            ),
        })

    ad_hoc_checks = []
    for row in ad_hoc_rows:
        day = row["session_date"]
        ad_hoc_checks.append({
            **{key: value for key, value in row.items()
               if key not in {"session_date", "supersedes_session_date"}},
            "session_date": day.isoformat(),
            "supersedes_session_date": (
                row["supersedes_session_date"].isoformat()
                if row["supersedes_session_date"] else None
            ),
            "tri_observation_present": day in session_set,
            "interpretation": (
                "TRI_OBSERVATION_ON_AD_HOC_CLOSURE_REVIEW"
                if day in session_set else "NO_TRI_OBSERVATION_ON_EFFECTIVE_CLOSURE_EXPECTED"
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
        annual_holidays = [
            day for day in intervening if day in effective_annual_holiday_dates
        ]
        ad_hoc_closures = [
            day for day in intervening
            if day in ad_hoc_closure_dates or day in revised_holiday_dates
        ]
        unexplained_weekdays = [
            day for day in intervening
            if day.weekday() < 5 and day not in effective_closure_dates
        ]
        gap_checks.append({
            "previous_session": previous.isoformat(),
            "next_session": following.isoformat(),
            "calendar_days_between": (following - previous).days,
            "intervening_dates": [day.isoformat() for day in intervening],
            "weekend_dates": [day.isoformat() for day in weekend_days],
            "annual_circular_holiday_dates": [day.isoformat() for day in annual_holidays],
            "ad_hoc_or_revised_closure_dates": [day.isoformat() for day in ad_hoc_closures],
            "unexplained_weekday_dates": [day.isoformat() for day in unexplained_weekdays],
            "status": (
                "NO_UNEXPLAINED_WEEKDAY_IN_GAP"
                if not unexplained_weekdays else "UNRESOLVED_WEEKDAY_GAP"
            ),
        })

    counts = {
        "candidate_holiday_rows": len(holiday_rows),
        "distinct_candidate_holiday_dates": len(holiday_dates),
        "annual_holiday_dates_superseded": len(superseded_dates),
        "effective_annual_holiday_dates": len(effective_annual_holiday_dates),
        "annual_holiday_dates_present_in_tri": sum(
            day in session_set for day in effective_annual_holiday_dates
        ),
        "superseded_annual_holiday_dates_present_in_tri": sum(
            day in session_set for day in superseded_dates
        ),
        "ad_hoc_or_revised_closure_dates": len(ad_hoc_rows),
        "ad_hoc_or_revised_closure_dates_absent_from_tri": sum(
            row["session_date"] not in session_set for row in ad_hoc_rows
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
        "gaps_explained_by_ad_hoc_or_revised_closure": sum(
            bool(row["ad_hoc_or_revised_closure_dates"]) for row in gap_checks
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
        "ad_hoc_closure_register_source": AD_HOC_REGISTER.as_posix(),
        "ad_hoc_closure_archive_source": AD_HOC_MANIFEST.as_posix(),
        "counts": counts,
        "holiday_date_checks": holiday_checks,
        "ad_hoc_closure_checks": ad_hoc_checks,
        "gap_checks": gap_checks,
        "interpretation": (
            "This is a diagnostic comparison only. Later NSE circulars can revise "
            "annual holiday dates; superseded dates are not treated as effective closures. "
            "A TRI observation on an effective closure requires session-type review. "
            "Unexplained weekdays may be missing data or other exchange events and must "
            "not be auto-classified. Archived bytes and extracted text remain pending "
            "independent source and semantic review."
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
