"""Extract archived NSE notice text and surface Nifty 50 references for review.

This is a deterministic evidence-preparation step, not an automated membership
classification. It never changes notice review statuses or creates intervals.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

INVENTORY = Path("data/reference/nifty50_annual_notice_inventory.csv")
REPORT = Path("data/reports/nifty50_notice_text_screening.json")
NIFTY50_RE = re.compile(r"nifty\\s*[- ]?\\s*50|nifty50", re.IGNORECASE)
CONTEXT_CHARS = 220


def _snippets(text: str, limit: int = 12) -> list[str]:
    snippets = []
    for match in NIFTY50_RE.finditer(text):
        start = max(0, match.start() - CONTEXT_CHARS)
        end = min(len(text), match.end() + CONTEXT_CHARS)
        snippet = re.sub(r"\\s+", " ", text[start:end]).strip()
        if snippet and (not snippets or snippet != snippets[-1]):
            snippets.append(snippet)
        if len(snippets) >= limit:
            break
    return snippets


def screen_pdf(path: Path, expected_sha256: str = "") -> dict:
    if not path.is_file():
        return {"text_status": "MISSING_SOURCE_DOCUMENT", "error": "source PDF is missing"}
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if not data.startswith(b"%PDF-"):
        return {"text_status": "INVALID_PDF_SIGNATURE", "source_sha256": digest}
    if expected_sha256 and digest != expected_sha256:
        return {"text_status": "SOURCE_HASH_MISMATCH", "source_sha256": digest}
    try:
        reader = PdfReader(str(path), strict=False)
        text = "\\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        return {"text_status": "PDF_TEXT_EXTRACTION_FAILED", "source_sha256": digest, "error": str(exc)}
    compact = re.sub(r"\\s+", " ", text).strip()
    if not compact:
        return {
            "text_status": "EMPTY_OR_SCANNED_PDF",
            "source_sha256": digest,
            "page_count": len(reader.pages),
            "text_characters": 0,
            "nifty50_mention_count": 0,
            "snippets": [],
        }
    snippets = _snippets(compact)
    return {
        "text_status": "EXTRACTED_NIFTY50_REFERENCE" if snippets else "EXTRACTED_NO_EXACT_NIFTY50_REFERENCE",
        "source_sha256": digest,
        "page_count": len(reader.pages),
        "text_characters": len(compact),
        "nifty50_mention_count": len(list(NIFTY50_RE.finditer(compact))),
        "snippets": snippets,
    }


def run_screening(inventory_path: Path = INVENTORY, report_path: Path = REPORT) -> dict:
    with inventory_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    results = []
    counts = {}
    for row in rows:
        source_path = Path(row.get("source_document_path", "")) if row.get("source_document_path") else Path("")
        result = screen_pdf(source_path, row.get("source_sha256", ""))
        status = result["text_status"]
        counts[status] = counts.get(status, 0) + 1
        results.append({
            "notice_id": row.get("notice_id", ""),
            "year": row.get("year", ""),
            "announcement_date": row.get("announcement_date", ""),
            "title": row.get("notes", ""),
            "source_url": row.get("source_url", ""),
            "review_status_unchanged": row.get("review_status", ""),
            **result,
        })
    report = {
        "inventory_rows_screened": len(rows),
        "screening_method": "pypdf text extraction plus exact Nifty 50/Nifty50 string matching",
        "status_counts": counts,
        "results": results,
        "classification_policy": (
            "Text hits and misses are triage only. No Nifty 50 scope is inferred; "
            "no review status, effective date, membership interval, or annual coverage flag is changed."
        ),
        "coverage_complete": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    return report


def main() -> None:
    report = run_screening()
    print(json.dumps({
        "inventory_rows_screened": report["inventory_rows_screened"],
        "status_counts": report["status_counts"],
        "coverage_complete": report["coverage_complete"],
    }, indent=2))
    if any(key in report["status_counts"] for key in ("SOURCE_HASH_MISMATCH", "INVALID_PDF_SIGNATURE")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
