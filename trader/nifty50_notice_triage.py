"""Build a conservative, non-mutating triage queue for the broad Nifty 50 notice inventory."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/reference/nifty50_annual_notice_inventory.csv"
DEFAULT_DETAILS = ROOT / "data/reports/nifty50_notice_triage.csv"
DEFAULT_SUMMARY = ROOT / "data/reports/nifty50_notice_triage.json"

OUT_OF_SCOPE_MARKERS = (
    "NO_FLAGSHIP_NIFTY50",
    "EXPLICIT_FIXED_INCOME_SDL_NOT_NIFTY50_EQUITY",
)


def classify(row: dict[str, str]) -> tuple[str, str]:
    """Classify work priority only; never certify an exclusion or membership event."""
    effect = (row.get("observed_nifty50_effect") or "").strip().upper()
    status = (row.get("review_status") or "").strip().upper()
    if effect == "UNCLASSIFIED_REVIEW_REQUIRED" or not effect:
        return (
            "UNRESOLVED_REVIEW_REQUIRED",
            "No explicit Nifty 50 scope/effect decision is recorded; inspect the primary document.",
        )
    if any(marker in effect for marker in OUT_OF_SCOPE_MARKERS):
        return (
            "OUT_OF_SCOPE_CANDIDATE_HUMAN_SIGNOFF",
            "Recorded screen indicates no flagship Nifty 50 membership effect; independent human sign-off is still required.",
        )
    if status == "CANDIDATE" or effect:
        return (
            "MEMBERSHIP_OR_EFFECTIVE_DATE_REVIEW",
            "Potential inclusion, exclusion, temporary constituent, or effective-date event; reconcile the full notice chain and primary source.",
        )
    return (
        "UNRESOLVED_REVIEW_REQUIRED",
        "No safe automated disposition; manual primary-source review required.",
    )


def build_triage(input_path: Path = DEFAULT_INPUT,
                 details_path: Path = DEFAULT_DETAILS,
                 summary_path: Path = DEFAULT_SUMMARY) -> dict:
    with input_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"notice_id", "year", "announcement_date", "effective_date",
                    "observed_nifty50_effect", "source_url", "source_document_path",
                    "source_sha256", "review_status", "notes"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"inventory missing required columns: {sorted(missing)}")
        rows = list(reader)

    output_rows = []
    by_category: Counter[str] = Counter()
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        category, reason = classify(row)
        by_category[category] += 1
        by_year[row.get("year", "")][category] += 1
        output_rows.append({
            **row,
            "triage_category": category,
            "triage_reason": reason,
            "human_review_required": "true",
            "human_signoff_status": "PENDING",
            "reviewer_name": "",
            "review_date": "",
            "review_decision_reason": "",
        })

    details_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output_rows[0]) if output_rows else [
        "notice_id", "year", "announcement_date", "effective_date",
        "observed_nifty50_effect", "source_url", "source_document_path",
        "source_sha256", "review_status", "notes", "triage_category",
        "triage_reason", "human_review_required", "human_signoff_status",
        "reviewer_name", "review_date", "review_decision_reason",
    ]
    with details_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    summary = {
        "input_path": str(input_path),
        "inventory_rows": len(rows),
        "triage_category_counts": dict(sorted(by_category.items())),
        "by_year": {
            year: dict(sorted(counts.items()))
            for year, counts in sorted(by_year.items())
        },
        "human_signoff_required_for_every_row": True,
        "membership_written": False,
        "source_rows_modified": False,
        "policy": (
            "This is a work-queue classification, not a source interpretation or verification. "
            "Out-of-scope candidates remain pending independent human sign-off. Potential "
            "membership/effective-date events require primary-source chain review. Unclassified "
            "rows remain unresolved. No membership intervals or source review states are changed."
        ),
        "details_csv": str(details_path),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--details", type=Path, default=DEFAULT_DETAILS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    print(json.dumps(build_triage(args.input, args.details, args.summary), indent=2))


if __name__ == "__main__":
    main()
