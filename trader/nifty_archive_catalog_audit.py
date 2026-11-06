"""Audit the complete NSE Indices archive catalog for discovery false negatives.

This is title-level triage only. It never classifies a notice as affecting or not
affecting Nifty 50, and never changes membership or annual coverage evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

CATALOG = Path("data/reference/nifty50_archive_discovery_catalog.csv")
REPORT = Path("data/reports/nifty50_archive_catalog_audit.json")
FIELDS = [
    "publication_date", "title", "source_url", "review_candidate",
    "scope_status", "first_discovered_at_utc",
]
BROAD_REVIEW_TERMS = re.compile(
    r"change|replacement|inclusion|exclusion|review|rebalanc|"
    r"reconstitution|constituent|demerger|merger|methodolog|criteria|"
    r"defer|revok|addition|removal|indices",
    re.IGNORECASE,
)
NON_EQUITY_HINTS = re.compile(
    r"fixed income|government bond|corporate bond|bharat bond|"
    r"SDL|G-?Sec|money market|strategy index|shariah|tata group",
    re.IGNORECASE,
)


def audit_catalog(catalog_path: Path = CATALOG, report_path: Path = REPORT) -> dict:
    with catalog_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Unexpected archive catalog schema: {reader.fieldnames}")
        rows = list(reader)

    missed = []
    for row in rows:
        if row.get("review_candidate", "").strip().lower() == "true":
            continue
        title = row.get("title", "").strip()
        if not BROAD_REVIEW_TERMS.search(title):
            continue
        missed.append({
            "publication_date": row.get("publication_date", ""),
            "title": title,
            "source_url": row.get("source_url", ""),
            "title_scope_hint": (
                "NON_EQUITY_OR_SPECIALIZED_INDEX_HINT"
                if NON_EQUITY_HINTS.search(title)
                else "GENERAL_INDEX_REVIEW_HINT"
            ),
            "scope_status_unchanged": row.get("scope_status", ""),
            "decision": "SOURCE_CONTENT_REVIEW_REQUIRED",
        })

    report = {
        "catalog_rows_audited": len(rows),
        "existing_review_candidates": sum(
            1 for row in rows
            if row.get("review_candidate", "").strip().lower() == "true"
        ),
        "non_candidate_rows": sum(
            1 for row in rows
            if row.get("review_candidate", "").strip().lower() != "true"
        ),
        "potential_false_negatives_for_source_review": len(missed),
        "potential_false_negatives": missed,
        "method": "Broad title-term scan over every catalog row not already marked review_candidate.",
        "safety_policy": (
            "Title hints are not scope decisions. No notice is classified as Nifty 50 "
            "change/no-change, no review status is changed, no effective date is inferred, "
            "and no membership interval or annual coverage flag is created."
        ),
        "coverage_complete": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    report = audit_catalog(args.catalog, args.report)
    print(json.dumps({
        "catalog_rows_audited": report["catalog_rows_audited"],
        "potential_false_negatives_for_source_review": report["potential_false_negatives_for_source_review"],
        "coverage_complete": report["coverage_complete"],
    }, indent=2))


if __name__ == "__main__":
    main()
