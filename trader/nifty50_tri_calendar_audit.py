"""Audit acquired NIFTY 50 TRI chronology and raw-source linkage.

This is a structural diagnostic only. It deliberately does not certify the
exchange trading calendar or authenticate the publisher series.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

CSV_PATH = Path("data/reference/nifty50_tri.csv")
REPORT_PATH = Path("data/reports/nifty50_tri_calendar_audit.json")


def audit(csv_path: Path = CSV_PATH) -> dict:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("TRI CSV has no observations")

    dates: list[date] = []
    year_counts: Counter[str] = Counter()
    weekend_sessions: list[str] = []
    raw_sources: dict[str, dict] = {}
    for line, row in enumerate(rows, start=2):
        try:
            day = date.fromisoformat(row["session_date"])
            value = float(row["tri_close"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid TRI row at CSV line {line}: {exc}") from exc
        if value <= 0:
            raise ValueError(f"non-positive TRI value at CSV line {line}")
        dates.append(day)
        year_counts[str(day.year)] += 1
        if day.weekday() >= 5:
            weekend_sessions.append(day.isoformat())
        evidence_path = Path(row["evidence_path"])
        evidence_hash = row["evidence_sha256"]
        if not evidence_path.is_file():
            raise ValueError(f"raw source response missing at CSV line {line}: {evidence_path}")
        if evidence_path.as_posix() not in raw_sources:
            raw_bytes = evidence_path.read_bytes()
            actual_hash = hashlib.sha256(raw_bytes).hexdigest()
            if actual_hash != evidence_hash:
                raise ValueError(f"raw source SHA-256 mismatch at CSV line {line}: {evidence_path}")
            raw_sources[evidence_path.as_posix()] = {
                "sha256": actual_hash,
                "bytes": len(raw_bytes),
                "rows_linked": 0,
            }
        elif raw_sources[evidence_path.as_posix()]["sha256"] != evidence_hash:
            raise ValueError(f"inconsistent evidence hash for {evidence_path}")
        raw_sources[evidence_path.as_posix()]["rows_linked"] += 1

    if dates != sorted(dates):
        raise ValueError("TRI session dates are not strictly chronological")
    if len(dates) != len(set(dates)):
        raise ValueError("duplicate TRI session dates")

    quarter_counts: Counter[str] = Counter()
    quarter_first: dict[str, str] = {}
    quarter_last: dict[str, str] = {}
    for day in dates:
        quarter = (day.month - 1) // 3 + 1
        key = f"{day.year}-Q{quarter}"
        quarter_counts[key] += 1
        quarter_first.setdefault(key, day.isoformat())
        quarter_last[key] = day.isoformat()

    expected_quarters = [
        f"{year}-Q{quarter}"
        for year in range(2018, 2025)
        for quarter in range(1, 5)
    ]
    quarterly_coverage = [
        {
            "quarter": key,
            "observation_count": quarter_counts.get(key, 0),
            "first_observation": quarter_first.get(key),
            "last_observation": quarter_last.get(key),
            "status": "OBSERVATIONS_PRESENT" if quarter_counts.get(key, 0) else "NO_OBSERVATIONS",
        }
        for key in expected_quarters
    ]

    gaps = []
    for previous, current in zip(dates, dates[1:]):
        delta = (current - previous).days
        if delta > 3:
            gaps.append({
                "previous_session": previous.isoformat(),
                "next_session": current.isoformat(),
                "calendar_days_between": delta,
            })

    return {
        "experiment_id": "NIFTY50_PILOT_001",
        "audit_type": "STRUCTURAL_CHRONOLOGY_AND_RAW_EVIDENCE_LINKAGE",
        "source_csv": CSV_PATH.as_posix(),
        "observation_count": len(rows),
        "first_session": dates[0].isoformat(),
        "last_session": dates[-1].isoformat(),
        "yearly_observation_counts": dict(sorted(year_counts.items())),
        "quarterly_observation_coverage": quarterly_coverage,
        "quarters_with_observations": sum(1 for row in quarterly_coverage if row["observation_count"] > 0),
        "quarters_expected": len(expected_quarters),
        "quarterly_observation_status": (
            "OBSERVATIONS_PRESENT_IN_ALL_28_QUARTERS"
            if all(row["observation_count"] > 0 for row in quarterly_coverage)
            else "ONE_OR_MORE_QUARTERS_HAVE_NO_OBSERVATIONS"
        ),
        "weekend_dated_observations": weekend_sessions,
        "gaps_over_three_calendar_days": gaps,
        "raw_source_files_verified": len(raw_sources),
        "raw_source_bytes_total": sum(x["bytes"] for x in raw_sources.values()),
        "raw_source_linked_observations": sum(x["rows_linked"] for x in raw_sources.values()),
        "chronology_and_hash_checks": "PASS",
        "calendar_completeness": "NOT_CERTIFIED_NO_INDEPENDENT_EXCHANGE_CALENDAR",
        "source_authenticity": "PENDING_INDEPENDENT_REVIEW",
        "reviewer": None,
        "holdout_access_authorized": False,
        "research_status": "RESEARCH_HOLD",
        "limitations": [
            "Weekend-dated observations are reported for review, not automatically rejected; special trading sessions may exist.",
            "Quarter counts prove only that observations exist in each calendar quarter; they do not prove all expected exchange sessions are present.",
            "Calendar gaps are diagnostics and are not interpreted as missing sessions without an authoritative exchange calendar.",
            "Hash linkage proves local bytes match the recorded digest, not that the source is authentic or semantically correct.",
            "No independent reviewer identity or sign-off is inferred.",
        ],
    }


def main() -> int:
    report = audit()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
