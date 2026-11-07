"""Fail-closed readiness audit for point-in-time Nifty 50 membership evidence.

This reports evidence gaps; it never infers constituents or authenticates source facts.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from trader.membership_evidence import audit_membership_evidence, audit_special_membership_events

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data" / "reference"
MEMBERSHIP_COLUMNS = {
    "symbol", "issuer_name", "security_identifier", "valid_from", "valid_to",
    "notice_id", "source_url", "source_published_at", "evidence_path",
    "evidence_sha256", "verification_status", "reviewer", "reviewed_at", "notes",
}


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return [], [f"{path.name}: missing CSV header"]
            return list(reader), []
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], [f"{path.name}: cannot read ({type(exc).__name__})"]


def audit_pit_readiness(reference_dir: Path = REFERENCE) -> dict:
    """Summarize membership evidence and fail closed until every required gate is met."""
    errors: list[str] = []
    membership_path = reference_dir / "nifty50_membership.csv"
    membership_rows, read_errors = _read_rows(membership_path)
    errors.extend(read_errors)
    if membership_rows:
        with membership_path.open(newline="", encoding="utf-8") as handle:
            columns = set(csv.DictReader(handle).fieldnames or [])
        missing = sorted(MEMBERSHIP_COLUMNS - columns)
        if missing:
            errors.append(f"nifty50_membership.csv: missing columns {missing}")
        for index, row in enumerate(membership_rows, start=2):
            if row.get("verification_status", "").strip() != "VERIFIED":
                errors.append(f"nifty50_membership.csv:{index}: interval is not VERIFIED")
            if not row.get("reviewer", "").strip() or not row.get("reviewed_at", "").strip():
                errors.append(f"nifty50_membership.csv:{index}: independent reviewer sign-off missing")
    else:
        errors.append("nifty50_membership.csv: no effective-dated membership intervals; header-only evidence is not PIT history")

    transition = audit_membership_evidence(
        reference_dir / "nifty50_transition_register.csv",
        reference_dir / "nifty50_annual_coverage.csv",
        reference_dir,
    )
    special = audit_special_membership_events(
        reference_dir / "nifty50_special_membership_events.csv"
    )
    errors.extend(transition["errors"])
    errors.extend(special["errors"])

    annual_rows, annual_read_errors = _read_rows(reference_dir / "nifty50_annual_coverage.csv")
    errors.extend(annual_read_errors)
    annual_incomplete = [
        row.get("year", "")
        for row in annual_rows
        if row.get("coverage_status", "").strip() != "COMPLETE"
    ]

    catalog_rows, catalog_errors = _read_rows(reference_dir / "nifty50_archive_discovery_catalog.csv")
    errors.extend(catalog_errors)
    unreviewed_catalog = sum(
        row.get("scope_status", "").strip() == "UNREVIEWED"
        for row in catalog_rows
    )
    inventory_rows, inventory_errors = _read_rows(reference_dir / "nifty50_annual_notice_inventory.csv")
    errors.extend(inventory_errors)
    unresolved_inventory = sum(
        row.get("review_status", "").strip() not in {
            "SCREENED_NO_NIFTY50_CHANGE", "VERIFIED", "ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW"
        }
        for row in inventory_rows
    )

    ready = (
        not errors
        and bool(membership_rows)
        and transition["ready"]
        and special["ready"]
        and not annual_incomplete
        and unreviewed_catalog == 0
        and unresolved_inventory == 0
    )
    return {
        "ready_for_pit_research": ready,
        "point_in_time_membership_verified": False,
        "membership_interval_rows": len(membership_rows),
        "membership_verified_rows": sum(
            row.get("verification_status", "").strip() == "VERIFIED"
            for row in membership_rows
        ),
        "transition_register": {
            "rows": transition["transition_rows"],
            "verified_rows": transition["verified_transition_rows"],
            "annual_years_complete": transition["annual_years_complete"],
            "annual_years_required": len(transition["annual_years_required"]),
            "ready": transition["ready"],
        },
        "special_membership": {
            "rows": special["rows"],
            "verified_rows": special["verified_rows"],
            "ready": special["ready"],
        },
        "annual_coverage_incomplete_years": annual_incomplete,
        "unreviewed_archive_catalog_rows": unreviewed_catalog,
        "unresolved_annual_notice_rows": unresolved_inventory,
        "errors": errors,
        "limitations": [
            "A passing structural audit does not authenticate NSE source documents or human interpretation.",
            "Point-in-time verification additionally requires independent review and complete 50-member effective-date snapshot reconciliation.",
            "No constituent is inferred from current membership, ticker coverage, or incomplete notice history.",
        ],
    }


def main() -> int:
    report = audit_pit_readiness()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready_for_pit_research"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
