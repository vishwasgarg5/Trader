#!/usr/bin/env python3
"""Archive observed official NSE corporate-filing frontend assets for endpoint discovery.

This step follows only script URLs actually referenced by an archived NSE landing page.
It records candidate API route strings found in those scripts but NEVER calls those routes.
That separation prevents guessed endpoints or undocumented calls from being mistaken for
verified filing data.
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
import urllib.request
from curl_cffi import requests as curl_requests
from datetime import datetime
from zoneinfo import ZoneInfo

from trader.market_source_fetcher import fetch_bytes

REPORT_IN = pathlib.Path("data/reports/weekly_market_document_refresh.json")
REPORT_OUT = pathlib.Path("data/reports/weekly_market_frontend_asset_audit.json")
ARCHIVE = pathlib.Path("data/reference/source_documents/weekly_market_frontend_assets")
MAX_BYTES = 5 * 1024 * 1024
ASSET_TIMEOUT = 60
MAX_ATTEMPTS = 2
MAX_WORKERS = 4
RETRY_BACKOFF_SECONDS = 2
ALLOWED_HOSTS = {"nseindia.com", "www.nseindia.com"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TraderResearchEvidenceBot/1.0; +https://github.com/vishwasgarg5/Trader)",
    "Accept": "application/javascript,text/javascript,*/*;q=0.5",
}
SCRIPT_RE = re.compile(r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)
ROUTE_RE = re.compile(r"""["'`]([^"'\`\s]{1,500})["'`]""")
RELEVANT_PATHS = ("/dist/js/components/corporate-filing/", "/dist/js/sections/corporate-filings.js")


def now_ist():
    return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()


def observed_script_urls(page_html: str, page_url: str):
    """Return only relevant script assets explicitly observed in official page HTML."""
    found, seen = [], set()
    for match in SCRIPT_RE.finditer(page_html):
        url = urllib.parse.urljoin(page_url, html.unescape(match.group(1).strip()))
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower()
        if (parsed.scheme == "https" and host in ALLOWED_HOSTS
                and any(parsed.path.startswith(path) for path in RELEVANT_PATHS)
                and url not in seen):
            seen.add(url)
            found.append(url)
    return found


def candidate_routes(script_text: str):
    """Extract route-like literals for human review; do not execute or request them."""
    routes = set()
    for match in ROUTE_RE.finditer(script_text):
        value = match.group(1)
        low = value.lower()
        # Only retain explicit API paths. Ordinary page/navigation paths may
        # contain words such as "corporate" or "announcements" but are not
        # evidence of an API contract.
        if value.startswith("/api/") and not value.startswith("//"):
            routes.add(value)
    return sorted(routes)


def fetch_asset(url: str):
    """Fetch an observed NSE asset through the shared HTTP/1.1-fallback client."""
    body, metadata = fetch_bytes(
        url,
        allowed_hosts=ALLOWED_HOSTS,
        headers=HEADERS,
        max_bytes=MAX_BYTES,
        timeout=(20, ASSET_TIMEOUT),
        attempts=3,
        expected_content_type=(),
        resume_path=ARCHIVE / ".partial" / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".part"),
    )
    final = urllib.parse.urlsplit(metadata["final_url"])
    content_type = metadata.get("content_type", "")
    if "javascript" not in content_type.lower() and not final.path.lower().endswith(".js"):
        raise ValueError(f"unexpected JavaScript content type: {content_type}")
    return body, content_type, metadata["final_url"], metadata

def inspect_asset(source_page_id: str, url: str):
    """Fetch and validate one observed asset; safe to run concurrently."""
    try:
        body, content_type, final_url, transport = fetch_asset(url)
        digest = hashlib.sha256(body).hexdigest()
        archive_path = ARCHIVE / f"{digest[:16]}_{pathlib.PurePosixPath(urllib.parse.urlsplit(final_url).path).name}"
        if not archive_path.exists():
            archive_path.write_bytes(body)
        text = body.decode("utf-8", errors="replace")
        return ({
            "source_page_id": source_page_id,
            "source_url": url,
            "final_url": final_url,
            "archive_path": archive_path.as_posix(),
            "bytes": len(body),
            "sha256": digest,
            "content_type": content_type,
            "transport": transport,
            "candidate_routes_for_manual_review": candidate_routes(text),
            "evidence_status": "OBSERVED_OFFICIAL_FRONTEND_ASSET_ARCHIVED",
            "route_execution_status": "NOT_CALLED",
        }, None)
    except Exception as exc:
        return (None, {
            "source_page_id": source_page_id,
            "source_url": url,
            "status": "ASSET_UNAVAILABLE_OR_REJECTED",
            "transport": getattr(exc, "metadata", {}),
            "error": f"{type(exc).__name__}: {exc}"[:800],
        })
def main():
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    report = json.loads(REPORT_IN.read_text(encoding="utf-8"))
    failures, seen, tasks = [], set(), []
    for page in report.get("records", []):
        if page.get("publisher") != "NSE":
            continue
        path = pathlib.Path(page.get("archive_path", ""))
        if not path.is_file():
            failures.append({"source_id": page.get("source_id"), "status": "PAGE_ARCHIVE_MISSING"})
            continue
        page_html = path.read_text(encoding="utf-8", errors="replace")
        for url in observed_script_urls(page_html, page.get("source_url", "")):
            if url not in seen:
                seen.add(url)
                tasks.append((page.get("source_id"), url))

    assets = []
    # Concurrent fetches keep bounded retries within the workflow's 20-minute job limit.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for asset, failure in pool.map(lambda task: inspect_asset(*task), tasks):
            if asset:
                assets.append(asset)
            if failure:
                failures.append(failure)

    output = {
        "schema_version": 1,
        "run_at_ist": now_ist(),
        "observed_asset_count": len(assets) + len(failures),
        "assets_archived": len(assets),
        "failures": failures,
        "assets": sorted(assets, key=lambda x: x["source_url"]),
        "status": "PARTIAL" if failures else ("ASSETS_ARCHIVED" if assets else "NO_RELEVANT_ASSETS_OBSERVED"),
        "limitations": [
            "Only script URLs explicitly observed in archived official NSE HTML are fetched.",
            "Route strings are candidates for manual review, not verified API contracts.",
            "No candidate route is called and no filing data is inferred from frontend code.",
            "This step does not update corporate-action ledgers, model data, prices, TRI, labels, or trading controls."
        ],
        "changes_to_model_data": False,
        "historical_prices_or_tri_modified": False,
        "holdout_accessed": False,
        "research_status": "RESEARCH_HOLD",
        "promotion_eligible": False,
        "paper_trading_eligible": False,
        "live_execution_enabled": False,
    }
    REPORT_OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("observed_asset_count", "assets_archived", "failures", "status")}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
