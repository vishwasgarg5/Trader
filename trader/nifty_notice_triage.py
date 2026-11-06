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
OCR_TEXT_DIR = Path("data/reference/ocr_notice_text")
CATALOG = Path("data/reference/nifty50_archive_discovery_catalog.csv")

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


def _ocr_page_text(pdf_path: Path, page_number: int) -> tuple[str, str]:
    """OCR one page; return extracted text and the Tesseract engine version."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("OCR requires pymupdf, pytesseract and Pillow") from exc

    with fitz.open(pdf_path) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        text = pytesseract.image_to_string(image, config="--psm 6")
        version = str(pytesseract.get_tesseract_version())
    return text.strip(), version


def _candidate_events(pdf_path: Path, source_sha256: str, notice_id: str) -> tuple[list[dict], str, dict | None]:
    if not pdf_path.is_file():
        return [], "MISSING_SOURCE_DOCUMENT", None
    raw = pdf_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not raw.startswith(b"%PDF-"):
        return [], "INVALID_PDF_SIGNATURE", None
    if source_sha256 and digest != source_sha256:
        return [], "SOURCE_HASH_MISMATCH", None
    try:
        reader = PdfReader(str(pdf_path), strict=False)
    except Exception:
        return [], "PDF_READ_FAILED", None
    events = []
    nonempty_pages = 0
    ocr_pages = []
    ocr_versions = set()
    for page_no, page in enumerate(reader.pages, start=1):
        page_text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
        if not page_text:
            ocr_text, engine_version = _ocr_page_text(pdf_path, page_no)
            if ocr_text:
                page_text = re.sub(r"\s+", " ", ocr_text).strip()
                ocr_pages.append({"page_number": page_no, "text": ocr_text})
                ocr_versions.add(engine_version)
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
            "candidate_symbols_unassigned": "; ".join(symbols),
            "candidate_out_symbols": "",
            "candidate_in_symbols": "",
            "supersession_cue": bool(SUPERSEDE.search(page_text)),
            "human_review_required": True,
            "page_text_excerpt": page_text[:1200],
        })
    ocr_metadata = None
    if ocr_pages:
        OCR_TEXT_DIR.mkdir(parents=True, exist_ok=True)
        ocr_path = OCR_TEXT_DIR / f"{notice_id}.txt"
        ocr_content = "\n\n".join(
            f"--- OCR page {item['page_number']} ---\n{item['text']}" for item in ocr_pages
        ) + "\n"
        ocr_path.write_text(ocr_content, encoding="utf-8")
        ocr_metadata = {
            "path": str(ocr_path),
            "sha256": hashlib.sha256(ocr_content.encode("utf-8")).hexdigest(),
            "pages": [item["page_number"] for item in ocr_pages],
            "engine": "Tesseract",
            "engine_versions": sorted(ocr_versions),
            "source_pdf_sha256": digest,
        }
    status = "OCR_EXTRACTED" if ocr_pages and nonempty_pages else (
        "EXTRACTED_TEXT" if nonempty_pages else "OCR_REQUIRED"
    )
    return events, status, ocr_metadata


def run(inventory_path: Path = INVENTORY, report_path: Path = REPORT,
        events_path: Path = EVENTS, catalog_path: Path = CATALOG) -> dict:
    with inventory_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    catalog_titles = {}
    if catalog_path.is_file():
        with catalog_path.open(newline="", encoding="utf-8") as f:
            for catalog_row in csv.DictReader(f):
                source_url = catalog_row.get("source_url", "").strip()
                title = catalog_row.get("title", "").strip()
                if source_url and title:
                    catalog_titles[source_url] = title
    triage, events, counts = [], [], {}
    ocr_artifacts = []
    for row in rows:
        title = row.get("notes", "")
        title = re.sub(r"^Archive title:\s*", "", title)
        priority = classify_title(title)
        counts[priority] = counts.get(priority, 0) + 1
        source_path = Path(row.get("source_document_path") or "")
        page_events, extraction_status, ocr_metadata = _candidate_events(
            source_path, row.get("source_sha256", ""), row.get("notice_id", "")
        )
        events.extend(page_events)
        if ocr_metadata:
            ocr_artifacts.append({"notice_id": row.get("notice_id", ""), **ocr_metadata})
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
            "ocr_metadata": ocr_metadata,
            "review_status_unchanged": row.get("review_status", ""),
        })
    report = {
        "inventory_rows": len(rows),
        "title_triage_counts": counts,
        "candidate_event_rows": len(events),
        "ocr_artifacts": ocr_artifacts,
        "ocr_required_notice_ids": [r["notice_id"] for r in triage if r["text_extraction_status"] == "OCR_REQUIRED"],
        "source_integrity_failures": [r["notice_id"] for r in triage if r["text_extraction_status"] in {"INVALID_PDF_SIGNATURE", "SOURCE_HASH_MISMATCH", "MISSING_SOURCE_DOCUMENT", "PDF_READ_FAILED"}],
        "triage": triage,
        "coverage_complete": False,
        "membership_written": False,
        "policy": "Title classes and page-level fields are candidate-generation only. Symbol lists are deliberately unassigned to in/out roles; dates are unnormalized text. Human verification against the source PDF is mandatory. No membership interval or review status is changed.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    events_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["notice_id", "source_sha256", "page_number", "candidate_effective_date_text",
               "candidate_symbols_unassigned", "candidate_out_symbols", "candidate_in_symbols", "supersession_cue",
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
    # Source-integrity failures are reported in the artifact. The workflow's
    # separate final gate fails the run after committing all diagnostic outputs.


if __name__ == "__main__":
    main()
