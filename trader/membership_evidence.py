"""Fail-closed validation for full point-in-time Nifty 50 evidence registers.

This validates completeness declarations and local evidence integrity. It cannot
independently authenticate NSE facts; VERIFIED rows still require human review.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import date
from pathlib import Path

YEARS = tuple(range(2018, 2025))
EVENT_COLUMNS = {
    "transition_id", "symbol", "action", "announcement_date", "effective_date",
    "source_url", "source_document_path", "source_sha256",
    "has_superseding_notice", "superseding_notice_url",
    "superseding_document_path", "superseding_sha256",
    "verification_status", "reviewer", "reviewed_at", "notes",
}
COVERAGE_COLUMNS = {
    "year", "scope_start", "scope_end", "official_notice_search_complete",
    "expected_transition_count", "verified_transition_count",
    "supersession_review_complete", "snapshot_reconciliation_complete",
    "independent_reviewer", "reviewed_at", "coverage_status", "notes",
}


def _read_csv(path: Path, required: set[str]) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = required.difference(reader.fieldnames or [])
            if missing:
                return [], [f"{path.name}: missing columns {sorted(missing)}"]
            return list(reader), []
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], [f"{path.name}: cannot read ({type(exc).__name__})"]


def _valid_digest_file(root: Path, relative: str, digest: str, label: str) -> list[str]:
    errors: list[str] = []
    rel = Path(relative)
    if not relative or rel.is_absolute() or ".." in rel.parts:
        return [f"{label}: evidence path must be a non-empty relative path without '..'"]
    base = root.resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return [f"{label}: evidence path escapes evidence root"]
    if not target.is_file():
        return [f"{label}: archived source document is missing ({relative})"]
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual.lower() != digest.lower():
        errors.append(f"{label}: SHA-256 mismatch for {relative}")
    return errors


def audit_membership_evidence(
    transition_path: Path,
    annual_coverage_path: Path,
    evidence_root: Path,
) -> dict:
    """Return a fail-closed readiness report for the 2018–2024 event ledger."""
    events, errors = _read_csv(transition_path, EVENT_COLUMNS)
    coverage, coverage_errors = _read_csv(annual_coverage_path, COVERAGE_COLUMNS)
    errors.extend(coverage_errors)

    seen_ids: set[str] = set()
    seen_events: set[tuple[str, str, str]] = set()
    verified_by_year = {year: 0 for year in YEARS}
    for row in events:
        event_id = row.get("transition_id", "").strip()
        label = event_id or "<blank transition_id>"
        if not event_id or event_id in seen_ids:
            errors.append(f"{label}: blank or duplicate transition_id")
        seen_ids.add(event_id)
        symbol = row.get("symbol", "").strip().upper()
        action = row.get("action", "").strip()
        if not symbol:
            errors.append(f"{label}: symbol is blank")
        if action not in {"ADD", "REMOVE"}:
            errors.append(f"{label}: action must be ADD or REMOVE")
        try:
            announcement = date.fromisoformat(row["announcement_date"])
            effective = date.fromisoformat(row["effective_date"])
            if announcement > effective:
                errors.append(f"{label}: announcement date is after effective date")
            if effective < date(2018, 4, 1) or effective > date(2024, 12, 31):
                errors.append(f"{label}: effective date is outside the 2018-04-01 to 2024-12-31 scope")
            event_key = (symbol, action, effective.isoformat())
            if event_key in seen_events:
                errors.append(f"{label}: duplicate symbol/action/effective-date event")
            seen_events.add(event_key)
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: invalid announcement_date/effective_date")
            effective = None

        if row.get("verification_status", "").strip() != "VERIFIED":
            errors.append(f"{label}: transition is not VERIFIED")
        else:
            if not row.get("reviewer", "").strip() or not row.get("reviewed_at", "").strip():
                errors.append(f"{label}: VERIFIED transition lacks reviewer sign-off")
            if not row.get("source_url", "").startswith("https://"):
                errors.append(f"{label}: VERIFIED transition lacks HTTPS source URL")
            errors.extend(_valid_digest_file(
                evidence_root, row.get("source_document_path", ""),
                row.get("source_sha256", ""), label,
            ))
            if effective is not None and effective.year in verified_by_year:
                verified_by_year[effective.year] += 1

        if row.get("has_superseding_notice", "").strip().lower() == "true":
            if not row.get("superseding_notice_url", "").startswith("https://"):
                errors.append(f"{label}: superseding notice URL is missing")
            errors.extend(_valid_digest_file(
                evidence_root, row.get("superseding_document_path", ""),
                row.get("superseding_sha256", ""), f"{label} superseding notice",
            ))
        elif row.get("has_superseding_notice", "").strip().lower() != "false":
            errors.append(f"{label}: has_superseding_notice must be true or false")

    coverage_by_year: dict[int, dict[str, str]] = {}
    for row in coverage:
        try:
            year = int(row.get("year", ""))
        except ValueError:
            errors.append("annual coverage row has invalid year")
            continue
        if year in coverage_by_year:
            errors.append(f"{year}: duplicate annual coverage row")
        coverage_by_year[year] = row

    for year in YEARS:
        row = coverage_by_year.get(year)
        if row is None:
            errors.append(f"{year}: annual coverage row is missing")
            continue
        expected_start = date(2018, 4, 1) if year == 2018 else date(year, 1, 1)
        expected_end = date(year, 12, 31)
        try:
            actual_start = date.fromisoformat(row.get("scope_start", ""))
            actual_end = date.fromisoformat(row.get("scope_end", ""))
            if actual_start != expected_start or actual_end != expected_end:
                errors.append(
                    f"{year}: scope must be {expected_start.isoformat()} through {expected_end.isoformat()}"
                )
        except ValueError:
            errors.append(f"{year}: invalid annual scope_start/scope_end")
        for field in (
            "official_notice_search_complete", "supersession_review_complete",
            "snapshot_reconciliation_complete",
        ):
            if row.get(field, "").strip().lower() != "true":
                errors.append(f"{year}: {field} is not true")
        try:
            expected = int(row.get("expected_transition_count", ""))
            declared_verified = int(row.get("verified_transition_count", ""))
        except ValueError:
            errors.append(f"{year}: expected/verified transition counts are not recorded")
            continue
        actual_verified = verified_by_year[year]
        if expected < 0 or declared_verified != expected or actual_verified != expected:
            errors.append(
                f"{year}: transition counts do not reconcile "
                f"(expected={expected}, declared_verified={declared_verified}, actual_verified={actual_verified})"
            )
        if row.get("coverage_status", "").strip() != "COMPLETE":
            errors.append(f"{year}: coverage_status is not COMPLETE")
        if not row.get("independent_reviewer", "").strip() or not row.get("reviewed_at", "").strip():
            errors.append(f"{year}: independent reviewer sign-off is missing")

    unexpected_years = sorted(set(coverage_by_year) - set(YEARS))
    if unexpected_years:
        errors.append(f"coverage contains out-of-scope years: {unexpected_years}")

    return {
        "ready": not errors and bool(events),
        "transition_rows": len(events),
        "verified_transition_rows": sum(verified_by_year.values()),
        "annual_years_required": list(YEARS),
        "annual_years_complete": sum(
            1 for year in YEARS
            if year in coverage_by_year
            and coverage_by_year[year].get("coverage_status", "").strip() == "COMPLETE"
        ),
        "errors": errors,
        "source_authenticity_independently_established": False,
    }


SPECIAL_EVENT_COLUMNS = {
    "event_id", "index_name", "member_key", "phase", "announcement_date",
    "effective_date", "constituent_count", "price_treatment", "source_url",
    "source_document_path", "source_sha256", "verification_status",
    "reviewer", "reviewed_at", "notes",
}
SPECIAL_PHASES = {"ADD_DUMMY", "REPLACE_DUMMY_WITH_LISTED", "REMOVE_LISTED"}


def audit_special_membership_events(path: Path) -> dict:
    """Fail closed unless temporary/dummy constituent episodes are represented and evidenced."""
    rows, errors = _read_csv(path, SPECIAL_EVENT_COLUMNS)
    required = {
        "N50-2023-JIOFIN-DUMMY-ADD": ("JIOFIN_SPINOFF_DUMMY", "ADD_DUMMY", "2023-07-20", 51),
        "N50-2023-JIOFIN-LIST": ("JIOFIN", "REPLACE_DUMMY_WITH_LISTED", "2023-08-21", 51),
        "N50-2023-JIOFIN-REMOVE": ("JIOFIN", "REMOVE_LISTED", "2023-09-07", 50),
    }
    by_id = {}
    for row in rows:
        event_id = row.get("event_id", "").strip()
        if not event_id or event_id in by_id:
            errors.append(f"{event_id or '<blank>'}: blank or duplicate special event_id")
        by_id[event_id] = row
        if row.get("phase", "").strip() not in SPECIAL_PHASES:
            errors.append(f"{event_id}: unsupported special membership phase")
        if row.get("index_name", "").strip().upper().replace(" ", "") != "NIFTY50":
            errors.append(f"{event_id}: index_name must be NIFTY 50")
        if not row.get("price_treatment", "").strip():
            errors.append(f"{event_id}: price_treatment is missing")
        try:
            announced = date.fromisoformat(row.get("announcement_date", ""))
            effective = date.fromisoformat(row.get("effective_date", ""))
            if announced > effective:
                errors.append(f"{event_id}: announcement_date is after effective_date")
        except ValueError:
            errors.append(f"{event_id}: invalid announcement/effective date")
        try:
            count = int(row.get("constituent_count", ""))
            if count not in {50, 51}:
                errors.append(f"{event_id}: constituent_count must be 50 or 51")
        except ValueError:
            errors.append(f"{event_id}: invalid constituent_count")
        if not row.get("source_url", "").startswith("https://"):
            errors.append(f"{event_id}: HTTPS primary source URL is missing")
        if row.get("verification_status", "").strip() != "VERIFIED":
            errors.append(f"{event_id}: special membership event is not VERIFIED")
        else:
            if not row.get("reviewer", "").strip() or not row.get("reviewed_at", "").strip():
                errors.append(f"{event_id}: VERIFIED special event lacks reviewer sign-off")
            errors.extend(_valid_digest_file(
                path.parent, row.get("source_document_path", ""),
                row.get("source_sha256", ""), event_id,
            ))
        if not row.get("notes", "").strip():
            errors.append(f"{event_id}: event treatment notes are missing")

    for event_id, (member, phase, effective, count) in required.items():
        row = by_id.get(event_id)
        if row is None:
            errors.append(f"{event_id}: required JIOFIN temporary-membership event is missing")
            continue
        if row.get("member_key", "").strip() != member:
            errors.append(f"{event_id}: member_key does not match the required demerger phase")
        if row.get("phase", "").strip() != phase:
            errors.append(f"{event_id}: phase does not match the required demerger phase")
        if row.get("effective_date", "").strip() != effective:
            errors.append(f"{event_id}: effective_date does not match the official event chronology")
        if row.get("constituent_count", "").strip() != str(count):
            errors.append(f"{event_id}: constituent_count does not match the demerger phase")
    if not set(required).issubset(by_id):
        errors.append("special membership ledger is missing one or more required JIOFIN episode rows")

    return {
        "ready": not errors and set(required).issubset(by_id),
        "rows": len(rows),
        "verified_rows": sum(row.get("verification_status", "").strip() == "VERIFIED" for row in rows),
        "errors": errors,
        "source_authenticity_independently_established": False,
    }
