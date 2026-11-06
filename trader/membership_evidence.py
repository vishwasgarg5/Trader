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
    verified_by_year = {year: 0 for year in YEARS}
    event_errors = 0
    for row in events:
        event_id = row.get("transition_id", "").strip()
        label = event_id or "<blank transition_id>"
        if not event_id or event_id in seen_ids:
            errors.append(f"{label}: blank or duplicate transition_id")
        seen_ids.add(event_id)
        if row.get("action", "").strip() not in {"ADD", "REMOVE"}:
            errors.append(f"{label}: action must be ADD or REMOVE")
        try:
            announcement = date.fromisoformat(row["announcement_date"])
            effective = date.fromisoformat(row["effective_date"])
            if announcement > effective:
                errors.append(f"{label}: announcement date is after effective date")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: invalid announcement_date/effective_date")
            announcement = effective = None

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
