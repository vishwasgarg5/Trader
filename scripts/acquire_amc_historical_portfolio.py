#!/usr/bin/env python3
"""Discover and acquire the official Motilal Oswal Dec-2024 portfolio via browser automation.

Only original XLSX response bytes from the AMC domain are eligible. The script never
opens and re-saves a workbook. It emits diagnostics even when the historical file
cannot be located.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

from playwright.sync_api import sync_playwright

BASE = "https://www.motilaloswalmf.com"
ARCHIVE = BASE + "/downloads/scheme-portfolio-details"
SCHEME_PAGE = BASE + "/mutual-funds/motilal-oswal-nifty-50-index-fund"
OUT = Path("acquisition-output")
OUT.mkdir(exist_ok=True)
events: list[dict] = []
candidates: list[dict] = []
downloaded: list[dict] = []

def record_response(response):
    try:
        url = response.url
        headers = response.headers
        ctype = headers.get("content-type", "")
        if any(x in url.lower() for x in ("portfolio", ".xlsx", ".xls", "api", "ajax")) or "spreadsheet" in ctype or "excel" in ctype:
            item = {"url": url, "status": response.status, "content_type": ctype,
                    "content_disposition": headers.get("content-disposition", "")}
            events.append(item)
            if response.status == 200 and urlparse(url).hostname == "www.motilaloswalmf.com":
                try:
                    body = response.body()
                    if body[:2] == b"PK" and len(body) > 5000:
                        candidates.append((item, body))
                except Exception as exc:
                    events.append({"body_read_error": str(exc), "url": url})
    except Exception as exc:
        events.append({"response_error": str(exc)})

def options_snapshot(page):
    data = []
    for i, sel in enumerate(page.locator("select").all()):
        try:
            data.append({"index": i, "name": sel.get_attribute("name"),
                         "id": sel.get_attribute("id"),
                         "aria": sel.get_attribute("aria-label"),
                         "options": sel.locator("option").all_text_contents()})
        except Exception:
            pass
    return data

def choose_matching_selects(page):
    # Use only visible UI options; no guessed API endpoints or fabricated file URLs.
    selects = page.locator("select")
    for i in range(selects.count()):
        sel = selects.nth(i)
        try:
            if not sel.is_visible():
                continue
            opts = sel.locator("option").evaluate_all(
                "(els) => els.map(e => ({text:(e.textContent||'').trim(), value:e.value}))"
            )
            for matcher in (lambda s: "2024" in s, lambda s: "december" in s.lower(),
                            lambda s: "nifty 50 index fund" in s.lower()):
                match = next((o for o in opts if matcher(o["text"]) and o["value"]), None)
                if match:
                    sel.select_option(match["value"], timeout=5000)
                    page.wait_for_timeout(1800)
        except Exception as exc:
            events.append({"select_error": str(exc), "index": i})

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(accept_downloads=True)
    page.on("response", record_response)
    for url in (ARCHIVE, SCHEME_PAGE):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            events.append({"page": url, "title": page.title(), "url_after_redirect": page.url,
                           "body_excerpt": re.sub(r"\\s+", " ", page.locator("body").inner_text())[:5000],
                           "selects": options_snapshot(page)})
            choose_matching_selects(page)
            events.append({"after_interaction": page.url, "selects": options_snapshot(page),
                           "body_excerpt": re.sub(r"\\s+", " ", page.locator("body").inner_text())[:5000]})
            for a in page.locator("a").all():
                try:
                    href = a.get_attribute("href") or ""
                    text = (a.inner_text() or "").strip()
                    if href and any(k in (href + " " + text).lower() for k in ("portfolio", ".xlsx", ".xls")):
                        events.append({"link_text": text, "href": href})
                except Exception:
                    pass
        except Exception as exc:
            events.append({"page_error": url, "error": str(exc)})
    browser.close()

# Save only a file whose own AMC response URL and on-page context identify the
# requested Nifty 50 December 2024 portfolio. Otherwise preserve diagnostics only.
for item, body in candidates:
    url = item["url"]
    filename = unquote(urlparse(url).path.rsplit("/", 1)[-1]) or "source.xlsx"
    if not filename.lower().endswith((".xlsx", ".xls")):
        filename = "amc_portfolio.xlsx"
    # A direct AMC response alone is not enough: the requested period and scheme
    # must be corroborated by the archive page state or source path.
    context = " ".join(str(e) for e in events).lower()
    period_ok = "december_2024" in url.lower() or ("december" in context and "2024" in context)
    scheme_ok = "nifty 50" in context and "index fund" in context
    if period_ok and scheme_ok:
        target = OUT / filename
        target.write_bytes(body)  # exact response bytes; no workbook re-save
        import hashlib
        downloaded.append({
            "source_url": url,
            "original_filename": filename,
            "byte_count": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "scheme_name": "Motilal Oswal Nifty 50 Index Fund",
            "as_of_date": "2024-12-31",
            "publication_date": None,
            "publication_date_reason": "Not established from the AMC response/page metadata in this run",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "retriever": "GitHub Actions automated browser acquisition",
            "source_type": "AMC_PRIMARY",
        })

(OUT / "browser_diagnostics.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
(OUT / "acquisition_result.json").write_text(json.dumps({
    "downloaded": downloaded,
    "candidate_xlsx_response_count": len(candidates),
    "status": "ACQUIRED" if downloaded else "NOT_ACQUIRED",
}, indent=2), encoding="utf-8")
print(json.dumps({"candidate_xlsx_response_count": len(candidates),
                  "downloaded": downloaded,
                  "diagnostic_events": len(events)}, indent=2))
