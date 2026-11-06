"""Title-first triage and page-level event candidates for Nifty 50 notices.

Outputs are review aids only: they never alter notice status or membership.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

INVENTORY = Path("data/reference/nifty50_annual_notice_inventory.csv")
REPORT = Path("data/reports/nifty50_notice_triage.json")
EVENTS = Path("data/reference/nifty50_candidate_events.csv")

# High-recall title cues for index constituent changes. Broad terms such as
# "change" alone are deliberately insufficient.
CHANGE_TITLE = re.compile(
    r"\b(change in indices|changes in indices|replacement(s)? of "
    r"(index )?constituents?|replacements? in indices|constituent "
    r"(replacement|change)|index reconstitution|semi.?annual review)\b",
    re.I,
)
NIFTY_TITLE = re.compile(r"\bnifty\s*[- ]?\s*50\b|\bnifty50\b", re.I)
EXCLUDE_TITLE = re.compile(
    r"fixed.?income|10 year sdl|strategy indices|midcap|smallcap|"
    r"hybrid indices|launch(es|ed)? .*indices|cessation of indices",
    re.I,
)
DATE_PATTERNS = [
    re.compile(r"\b(?:w\.e\.f\.?|with effect from|effective from|effective date[: ]+)\s*"
               r"([0-3]?\d\s+[A-Za-z]+\s+20\d{2}|[A-Za-z]+\s+[0-3]?\d,?\s+20\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2})", re.I),
]
SYMBOL = re.compile(r"\b[A-Z][A-Z0-9&.-]{1,14}(?:\.NS)?\b")
OUT_CUE = re.compile(r"\b(remove[sd]?|exclud(?:e|ed|ing)|replace[sd]?|replac(?:ed|ement of))\b", re.I)
IN_CUE = re.compile(r"\b(add(?:ed|ition)?|includ(?:e|ed|ing)|replace[sd]? with)\b", re.I)
SUPERSEDE = re.compile(r"\b(supersed(?:e|es|ed|ing)|in place of|withdrawn|revok(?:e|ed|ing)|corrigendum|revised notice)\b", re.I)


def classify_title(title: str) -> str:
    title = title or ""
    if EXCLUDE_TITLE.search(title) and not NIFTY_TITLE.search(title):
        return "LOW_PRIORITY_LIKELY_OTHER_INDEX"
    if NIFTY_TITLE.search(title) or CHANGE_TITLE.search(title):
        return "PRIORITY_CONSTITUENT_CHANGE_REVIEW"
    return "LOW_PRIORITY_GENERAL_ARCHIVE_REVIEW"


def _candidate_events(pdf_path: Path, source_sha256: str, notice_id: str) -> tuple[list[dict], str]:
    if not pdf_path.is_file():
        return [], "MISSING_SOURCE_DOCUMENT"
    raw = pdf_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not raw.startswith(b"%PDF-"):
        return [], "INVALID_PDF_SIGNATURE"
    if source_sha256 and digest != source_sha256:
        return [], "SOURCE_HASH_MISMATCH"
    try:
        reader = PdfReader(str(pdf_path), strict=False)
    except Exception:
        return [], "PDF_READ_FAILED"
    events = []
    nonempty_pages = 0
    for page_no, page in enumerate(reader.pages, start=1):
        page_text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
        if not page_text:
            continue
        nonempty_pages += 1
        dates = [m.group(1) for pattern in DATE_PATTERNS for m in pattern.finditer(page_text)]
        symbols = sorted(set(SYMBOL.findall(page_text)))
        # Keep the page as a candidate if it contains an event cue or an
        # explicit Nifty 50 mention; humans must resolve role/date/scope.
        if not (OUT_CUE.search(page_text) or IN_CUE.search(page_text) or NIFTY_TITLE.search(page_text)):
            continue
        events.append({
            "notice_id": notice_id,
            "source_sha256": digest,
            "page_number": page_no,
            "candidate_effective_date_text": "; ".join(dates),
            "candidate_out_symbols": "; ".join(symbols) if OUT_CUE.search(page_text) else "",
            "candidate_in_symbols": "; ".join(symbols) if IN_CUE.search(page_text) else "",
            "supersession_cue": bool(SUPERSEDE.search(page_text)),
            "human_review_required": True,
            "page_text_excerpt": page_text[:1200],
        })
    return events, "EXTRACTED_TEXT" if nonempty_pages else "OCR_REQUIRED"


def run(inventory_path: Path = INVENTORY, report_path: Path = REPORT,
        events_path: Path = EVENTS) -> dict:
    with inventory_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    triage, events, counts = [], [], {}
    for row in rows:
        title = row.get("notes", "")
        title = re.sub(r"^Archive title:\s*", "", title)
        priority = classify_title(title)
        counts[priority] = counts.get(priority, 0) + 1
        source_path = Path(row.get("source_document_path") or "")
        page_events, extraction_status = _candidate_events(
            source_path, row.get("source_sha256", ""), row.get("notice_id", "")
        )
        events.extend(page_events)
        triage.append({
            "notice_id": row.get("notice_id", ""),
            "announcement_date": row.get("announcement_date", ""),
            "title": title,
            "source_url": row.get("source_url", ""),
            "source_document_path": row.get("source_document_path", ""),
            "source_sha256_expected": row.get("source_sha256", ""),
            "title_triage": priority,
            "text_extraction_status": extraction_status,
            "candidate_page_count": len(page_events),
            "review_status_unchanged": row.get("review_status", ""),
        })
    report = {
        "inventory_rows": len(rows),
        "title_triage_counts": counts,
        "candidate_event_rows": len(events),
        "ocr_required_notice_ids": [r["notice_id"] for r in triage if r["text_extraction_status"] == "OCR_REQUIRED"],
        "source_integrity_failures": [r["notice_id"] for r in triage if r["text_extraction_status"] in {"INVALID_PDF_SIGNATURE", "SOURCE_HASH_MISMATCH", "MISSING_SOURCE_DOCUMENT", "PDF_READ_FAILED"}],
        "triage": triage,
        "coverage_complete": False,
        "membership_written": False,
        "policy": "Title classes and page-level fields are candidate-generation only. Symbol lists are not assigned to in/out roles; dates are unnormalized text. Human verification against the source PDF is mandatory. No membership interval or review status is changed.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    events_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["notice_id", "source_sha256", "page_number", "candidate_effective_date_text",
               "candidate_out_symbols", "candidate_in_symbols", "supersession_cue",
               "human_review_required", "page_text_excerpt"]
    with events_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(events)
    return report


def main() -> None:
    report = run()
    print(json.dumps({k: report[k] for k in (
        "inventory_rows", "title_triage_counts", "candidate_event_rows",
        "ocr_required_notice_ids", "source_integrity_failures", "coverage_complete"
    )}, indent=2))
    if report["source_integrity_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
