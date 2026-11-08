#!/usr/bin/env python3
"""Extract review candidates from archived NSE annual holiday circular PDFs.

This is a text-extraction aid, not an authoritative trading-calendar parser.
Every extracted date remains a candidate until independent source review and
session-level reconciliation are completed.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

from pypdf import PdfReader

MANIFEST = Path("data/reports/nifty50_tri_holiday_circular_archive.json")
REPORT = Path("data/reports/nifty50_tri_holiday_extraction.json")
TEXT_ROOT = Path("data/reference/extracted_text/nse_holiday_circulars")
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
WEEKDAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
ROW_START = re.compile(
    rf"^\s*(\d{{1,2}})\s+({MONTHS})\s+(\d{{1,2}}),?\s*(20\d{{2}})\s*(.*)$",
    re.I,
)
WEEKDAY_START = re.compile(rf"^\s*({WEEKDAYS})\b\s*(.*)$", re.I)


def extract_candidates(text: str, expected_year: int, page_number: int) -> list[dict]:
    lines = text.splitlines()
    candidates = []
    table_type = "WEEKDAY_HOLIDAY_TABLE"
    for index, line in enumerate(lines):
        if "holidays falling on saturday" in line.lower():
            table_type = "WEEKEND_DATED_HOLIDAY_TABLE"
        match = ROW_START.match(line)
        if not match:
            continue
        row_number, month, day, year, tail = match.groups()
        if int(year) != expected_year:
            continue
        try:
            parsed = datetime.strptime(f"{month} {int(day):02d} {year}", "%B %d %Y").date()
        except ValueError:
            continue

        weekday = None
        description = ""
        weekday_match = WEEKDAY_START.match(tail)
        if weekday_match:
            weekday, description = weekday_match.groups()
        else:
            # Some NSE PDFs split the weekday/description onto the next line.
            for lookahead in lines[index + 1:index + 4]:
                candidate = WEEKDAY_START.match(lookahead)
                if candidate:
                    weekday, description = candidate.groups()
                    break
                if ROW_START.match(lookahead):
                    break

        candidates.append({
            "date": parsed.isoformat(),
            "weekday_in_source": weekday,
            "weekday_matches_date": (
                parsed.strftime("%A").lower() == weekday.lower() if weekday else None
            ),
            "description": re.sub(r"\s+", " ", description).strip() or None,
            "table_type": table_type,
            "row_number": int(row_number),
            "page_number": page_number,
            "source_text_line_number": index + 1,
            "review_status": "UNREVIEWED_EXTRACTION_CANDIDATE",
        })
    return candidates


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records, errors = [], []
    TEXT_ROOT.mkdir(parents=True, exist_ok=True)
    for item in manifest.get("records", []):
        year = int(item["year"])
        pdf_path = Path(item["archive_path"])
        try:
            raw = pdf_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != item["sha256"]:
                raise ValueError("PDF SHA-256 differs from acquisition manifest")
            reader = PdfReader(str(pdf_path), strict=True)
            pages, candidates = [], []
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                pages.append(page_text)
                candidates.extend(extract_candidates(page_text, year, page_number))
            text_path = TEXT_ROOT / f"{year}_{item['circular_reference']}.txt"
            extracted_text = "\n\n".join(
                f"===== PAGE {i} =====\n{page}" for i, page in enumerate(pages, start=1)
            )
            text_path.write_text(extracted_text + "\n", encoding="utf-8")
            records.append({
                "year": year,
                "circular_reference": item["circular_reference"],
                "pdf_path": pdf_path.as_posix(),
                "pdf_sha256_verified": digest,
                "page_count": len(reader.pages),
                "extracted_text_path": text_path.as_posix(),
                "extracted_text_sha256": hashlib.sha256(extracted_text.encode("utf-8")).hexdigest(),
                "candidate_date_count": len(candidates),
                "candidate_dates": candidates,
                "weekday_mismatch_count": sum(
                    row["weekday_matches_date"] is False for row in candidates
                ),
                "missing_source_weekday_count": sum(
                    row["weekday_in_source"] is None for row in candidates
                ),
                "extraction_status": "ROW_TEXT_EXTRACTED_REVIEW_REQUIRED",
                "independent_review_status": "PENDING",
            })
        except Exception as exc:
            errors.append({"year": year, "pdf_path": pdf_path.as_posix(), "error": str(exc)})
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "purpose": "Extract row-level candidate holiday dates and searchable text from archived NSE CMTR circulars",
        "source_manifest": MANIFEST.as_posix(),
        "expected_years": list(range(2018, 2025)),
        "extracted_years": [r["year"] for r in records],
        "extracted_count": len(records),
        "expected_count": 7,
        "records": records,
        "errors": errors,
        "interpretation": "Row-level machine-extracted dates are candidates only. Weekday mismatches and missing weekday fields are review flags, not automatic corrections. Weekend rows, special sessions, revised circulars, and completeness require independent review and reconciliation against authoritative exchange records.",
        "calendar_completeness": "NOT_CERTIFIED",
        "independent_review_status": "PENDING",
        "research_status": "RESEARCH_HOLD",
        "holdout_access_authorized": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "extracted_years": report["extracted_years"],
        "extracted_count": report["extracted_count"],
        "candidate_date_counts": {str(r["year"]): r["candidate_date_count"] for r in records},
        "weekday_mismatch_counts": {str(r["year"]): r["weekday_mismatch_count"] for r in records},
        "missing_weekday_counts": {str(r["year"]): r["missing_source_weekday_count"] for r in records},
        "errors": errors,
        "calendar_completeness": "NOT_CERTIFIED",
    }, indent=2))
    return 0 if not errors and sorted(r["year"] for r in records) == list(range(2018, 2025)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
