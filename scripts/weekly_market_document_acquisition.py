#!/usr/bin/env python3
"""Download only explicitly linked primary-source PDF documents from the weekly discovery report.

The downloader is intentionally conservative: it follows same-publisher NSE/BSE links only,
requires a PDF signature, hashes the exact bytes, and never interprets events or updates ledgers.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

REPORT_IN = pathlib.Path("data/reports/weekly_market_document_refresh.json")
REPORT_OUT = pathlib.Path("data/reports/weekly_market_document_acquisition.json")
ARCHIVE = pathlib.Path("data/reference/source_documents/weekly_market_documents")
MAX_BYTES = 25 * 1024 * 1024
TIMEOUT = 20
MAX_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 2
ALLOWED_HOSTS = {"nseindia.com", "www.nseindia.com", "nsearchives.nseindia.com",
                 "bseindia.com", "www.bseindia.com", "niftyindices.com", "www.niftyindices.com"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TraderResearchEvidenceBot/1.0; +https://github.com/vishwasgarg5/Trader)",
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.5",
}

def now_ist():
    return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

def safe_pdf_url(base_url: str, href: str):
    url = urllib.parse.urljoin(base_url, href)
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS:
        return None
    path = parsed.path.lower()
    if not (path.endswith(".pdf") or ".pdf?" in url.lower()):
        return None
    if parsed.username or parsed.password:
        return None
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))

def open_with_retry(request, timeout):
    """Retry transient network failures once; never retry validation failures."""
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except (TimeoutError, urllib.error.URLError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500 and exc.code != 429:
                raise
            last_error = exc
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise last_error

def download_one(item):
    url, source_id, publisher = item
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with open_with_retry(request, timeout=TIMEOUT) as response:
            final_url = response.geturl()
            final = urllib.parse.urlsplit(final_url)
            if final.scheme != "https" or (final.hostname or "").lower() not in ALLOWED_HOSTS:
                raise ValueError("redirect left official NSE/BSE host allowlist")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("document exceeded 25 MiB safety limit")
            if not body.startswith(b"%PDF-"):
                raise ValueError("response does not have a PDF file signature")
            digest = hashlib.sha256(body).hexdigest()
            name = pathlib.PurePosixPath(urllib.parse.urlsplit(final_url).path).name
            if not name or name in {".", ".."}:
                name = digest[:16] + ".pdf"
            name = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:160]
            path = ARCHIVE / digest[:2] / f"{digest[:16]}_{name}"
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(body)
            return {
                "source_id": source_id, "publisher": publisher, "source_url": url,
                "final_url": final_url, "archive_path": path.as_posix(),
                "bytes": len(body), "sha256": digest,
                "content_type": response.headers.get("Content-Type", ""),
                "retrieved_at_ist": now_ist(),
                "evidence_status": "PRIMARY_SOURCE_PDF_BYTES_ARCHIVED",
                "semantic_review_status": "NOT_REVIEWED",
            }, None
    except Exception as exc:
        return None, {
            "source_id": source_id, "publisher": publisher, "source_url": url,
            "status": "DOCUMENT_UNAVAILABLE_OR_REJECTED",
            "error": f"{type(exc).__name__}: {exc}"[:1000],
        }

def main():
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    report = json.loads(REPORT_IN.read_text(encoding="utf-8"))
    candidates, seen = [], set()
    for record in report.get("records", []):
        base = record.get("source_url", "")
        publisher = record.get("publisher", "")
        source_id = record.get("source_id", "")
        for link in record.get("links", []):
            url = safe_pdf_url(base, link.get("href", ""))
            if url and url not in seen:
                seen.add(url)
                candidates.append((url, source_id, publisher))
    archived, failures = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download_one, item) for item in candidates]
        for future in as_completed(futures):
            ok, error = future.result()
            if ok:
                archived.append(ok)
            elif error:
                failures.append(error)
    output = {
        "schema_version": 1,
        "run_at_ist": now_ist(),
        "discovered_pdf_candidates": len(candidates),
        "pdf_documents_archived": len(archived),
        "document_failures": failures,
        "documents": sorted(archived, key=lambda x: x["sha256"]),
        "status": "NO_PDF_LINKS_DISCOVERED" if not candidates else (
            "PARTIAL" if failures else "PDF_BYTES_ARCHIVED"
        ),
        "limitations": [
            "Only PDF links explicitly present in successfully acquired official landing-page HTML are considered.",
            "JavaScript-only listings, API-fed tables, and documents behind interactive sessions may not be discovered.",
            "PDF signature and host allowlisting do not establish issuer authenticity or event meaning.",
            "No event extraction, correction/supersession decision, independent review, or corporate-action ledger update occurs.",
            "Point-in-time NIFTY 50 membership remains a prerequisite for issuer-specific filtering.",
        ],
        "changes_to_model_data": False,
        "historical_prices_or_tri_modified": False,
        "holdout_accessed": False,
        "research_status": "RESEARCH_HOLD",
        "promotion_eligible": False,
        "paper_trading_eligible": False,
        "live_execution_enabled": False,
    }
    REPORT_OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in (
        "discovered_pdf_candidates", "pdf_documents_archived", "document_failures", "status"
    )}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
