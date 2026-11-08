#!/usr/bin/env python3
"""Weekly discovery snapshot of official NSE/BSE market-document landing pages.

This is a discovery/archive layer, not an issuer-event extractor. It preserves
successful raw HTML responses and hashes, indexes visible links, and explicitly
fails closed when point-in-time NIFTY 50 membership or primary-source access is
missing. It never mutates prices, labels, TRI, model state, or execution gates.
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(".")
ARCHIVE = ROOT / "data/reference/source_documents/weekly_market_pages"
REPORT = ROOT / "data/reports/weekly_market_document_refresh.json"
MEMBERSHIP = ROOT / "data/reference/nifty50_membership.csv"
MAX_BYTES = 20 * 1024 * 1024
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TraderResearchEvidenceBot/1.0; +https://github.com/vishwasgarg5/Trader)",
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

SOURCES = [
    ("NSE_ANNOUNCEMENTS", "https://www.nseindia.com/companies-listing/corporate-filings-announcements"),
    ("NSE_CORPORATE_ACTIONS", "https://www.nseindia.com/companies-listing/corporate-filings-actions"),
    ("NSE_BUYBACKS", "https://www.nseindia.com/companies-listing/corporate-filings-daily-buy-back"),
    ("NSE_HOLIDAYS", "https://www.nseindia.com/resources/exchange-communication-holidays"),
    ("BSE_ANNOUNCEMENTS", "https://www.bseindia.com/corporates/ann.html"),
    ("BSE_CORPORATE_ACTIONS", "https://www.bseindia.com/corporates/corporate_act.html"),
    ("BSE_NOTICES_CIRCULARS", "https://www.bseindia.com/markets/MarketInfo/NoticesCirculars.aspx"),
]

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_data(self, data):
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            label = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
            href = html.unescape(self._href.strip())
            if href:
                self.links.append({"label": label[:500], "href": href})
            self._href = None
            self._parts = []

def now_ist():
    return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

def fetch(url: str):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError(f"response exceeded {MAX_BYTES} byte safety limit")
        content_type = response.headers.get("Content-Type", "")
        status = getattr(response, "status", 200)
        if status != 200:
            raise ValueError(f"HTTP {status}")
        if not (body.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<?xml"))
                or "html" in content_type.lower()):
            raise ValueError(f"unexpected content type: {content_type}")
        return body, content_type, response.headers.get("Last-Modified")

def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    run_at = now_ist()
    records, failures = [], []
    for source_id, url in SOURCES:
        try:
            body, content_type, last_modified = fetch(url)
            digest = hashlib.sha256(body).hexdigest()
            path = ARCHIVE / f"{source_id.lower()}_{digest[:16]}.html"
            path.write_bytes(body)
            parser = LinkParser()
            parser.feed(body.decode("utf-8", errors="replace"))
            records.append({
                "source_id": source_id,
                "publisher": "NSE" if source_id.startswith("NSE_") else "BSE",
                "source_url": url,
                "retrieved_at_ist": run_at,
                "http_content_type": content_type,
                "http_last_modified": last_modified,
                "archive_path": path.as_posix(),
                "bytes": len(body),
                "sha256": digest,
                "visible_link_count": len(parser.links),
                "links": parser.links[:5000],
                "evidence_status": "OFFICIAL_LANDING_PAGE_BYTES_ARCHIVED",
                "semantic_review_status": "NOT_REVIEWED",
            })
        except Exception as exc:
            failures.append({
                "source_id": source_id,
                "publisher": "NSE" if source_id.startswith("NSE_") else "BSE",
                "source_url": url,
                "retrieved_at_ist": run_at,
                "status": "SOURCE_UNAVAILABLE_OR_UNPARSEABLE",
                "error": f"{type(exc).__name__}: {exc}"[:1000],
            })

    membership_rows = 0
    if MEMBERSHIP.exists():
        lines = MEMBERSHIP.read_text(encoding="utf-8-sig").splitlines()
        membership_rows = max(0, len([line for line in lines if line.strip()]) - 1)

    report = {
        "schema_version": 1,
        "run_at_ist": run_at,
        "scope": {
            "exchange_wide_sources": ["NSE", "BSE"],
            "issuer_scope": "NIFTY50_PILOT_001_ONLY",
            "requested_document_types": [
                "circulars", "notices", "trading_holidays", "special_sessions",
                "market_timings", "settlement_changes", "dividends", "buybacks",
                "bonus_issues", "splits", "rights_issues", "mergers_demergers",
                "board_meetings", "financial_results", "material_disclosures",
                "corrections", "cancellations", "superseding_notices"
            ],
        },
        "discovery_status": "PARTIAL" if failures else "LANDING_PAGES_ACQUIRED",
        "landing_pages_expected": len(SOURCES),
        "landing_pages_archived": len(records),
        "source_failures": failures,
        "membership_register_rows": membership_rows,
        "issuer_filter_status": (
            "BLOCKED_EMPTY_POINT_IN_TIME_MEMBERSHIP_REGISTER"
            if membership_rows == 0 else
            "MEMBERSHIP_ROWS_PRESENT_BUT_INDEPENDENT_VERIFICATION_MUST_BE_CHECKED"
        ),
        "records": records,
        "limitations": [
            "Landing-page HTML is discovery evidence only; it is not the underlying circular or issuer filing.",
            "Visible links are not proof that all exchange documents were enumerated.",
            "No issuer events are promoted into the verified corporate-action ledger by this script.",
            "No PDF/filing bytes are archived unless a separate document-acquisition step downloads and validates them.",
            "A SHA-256 digest proves downloaded-byte integrity only, not publisher authenticity or document meaning.",
            "No event extraction, supersession decision, or independent review is performed here.",
            "The point-in-time NIFTY 50 membership register must be populated and independently verified before issuer-specific inclusion is automated."
        ],
        "changes_to_model_data": False,
        "historical_prices_or_tri_modified": False,
        "holdout_accessed": False,
        "research_status": "RESEARCH_HOLD",
        "promotion_eligible": False,
        "paper_trading_eligible": False,
        "live_execution_enabled": False,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "run_at_ist": run_at,
        "landing_pages_archived": len(records),
        "landing_pages_expected": len(SOURCES),
        "source_failures": failures,
        "membership_register_rows": membership_rows,
        "discovery_status": report["discovery_status"],
    }, indent=2))
    # Preserve the report even when some exchange endpoints block automated access.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
