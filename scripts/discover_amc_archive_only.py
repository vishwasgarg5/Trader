#!/usr/bin/env python3
"""Inspect official AMC archive UI/network metadata without downloading files.

This is discovery-only, not an acquisition attempt. It loads the official archive
page, records visible controls and request/response metadata, and never clicks,
selects, follows file links, reads response bodies, or saves downloads.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

SOURCES = {
    "navi": {
        "url": "https://navi.com/mutual-fund/downloads/portfolio/",
        "host": "navi.com",
    },
    "aditya-birla-sun-life": {
        "url": "https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio",
        "host": "mutualfund.adityabirlacapital.com",
    },
}

def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SOURCES:
        raise SystemExit("Usage: discover_amc_archive_only.py navi|aditya-birla-sun-life")
    key = sys.argv[1]
    source = SOURCES[key]
    out = Path("discovery-output")
    out.mkdir(exist_ok=True)
    requests: list[dict] = []
    responses: list[dict] = []
    downloads: list[dict] = []
    controls: list[dict] = []
    errors: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(accept_downloads=False)
        page = context.new_page()

        def on_request(req):
            parsed = urlparse(req.url)
            requests.append({
                "url": req.url,
                "method": req.method,
                "resource_type": req.resource_type,
                "host": parsed.hostname,
                "is_official_amc_domain": parsed.hostname == source["host"]
                    or (parsed.hostname or "").endswith("." + source["host"]),
            })

        def on_response(resp):
            parsed = urlparse(resp.url)
            responses.append({
                "url": resp.url,
                "status": resp.status,
                "content_type": resp.headers.get("content-type"),
                "content_disposition": resp.headers.get("content-disposition"),
                "host": parsed.hostname,
                "is_official_amc_domain": parsed.hostname == source["host"]
                    or (parsed.hostname or "").endswith("." + source["host"]),
            })

        def on_download(download):
            # Cancel immediately; record the event as a safety violation for review.
            downloads.append({"suggested_filename": download.suggested_filename,
                              "url": download.url, "cancelled": True})
            download.cancel()

        page.on("request", on_request)
        page.on("response", on_response)
        page.on("download", on_download)
        try:
            page.goto(source["url"], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            for index, element in enumerate(page.locator("select, input, button, [role=combobox], [role=button]").all()):
                try:
                    controls.append({
                        "index": index,
                        "tag": element.evaluate("(e) => e.tagName.toLowerCase()"),
                        "type": element.get_attribute("type"),
                        "name": element.get_attribute("name"),
                        "id": element.get_attribute("id"),
                        "role": element.get_attribute("role"),
                        "aria_label": element.get_attribute("aria-label"),
                        "text": (element.inner_text(timeout=1000) or "")[:500],
                        "value": element.input_value(timeout=1000) if element.evaluate("(e) => ['INPUT','SELECT'].includes(e.tagName)") else None,
                        "options": element.locator("option").all_text_contents() if element.evaluate("(e) => e.tagName === 'SELECT'") else [],
                    })
                except Exception as exc:
                    controls.append({"index": index, "inspection_error": str(exc)})
        except Exception as exc:
            errors.append({"page_error": str(exc), "current_url": page.url})
        finally:
            browser.close()

    record = {
        "record_type": "AMC_ARCHIVE_DISCOVERY_ONLY",
        "counts_as_acquisition_attempt": False,
        "acquisition_attempts_consumed": 0,
        "downloads_permitted": False,
        "amc": key,
        "official_archive_url": source["url"],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "final_url": page.url if not page.is_closed() else None,
        "controls": controls,
        "requests": requests,
        "responses": responses,
        "download_events_cancelled": downloads,
        "errors": errors,
        "limitations": [
            "No controls were changed and no buttons or links were clicked.",
            "No response bodies were read or persisted.",
            "No workbook or other file was downloaded.",
            "Network calls are metadata only; file/API payload completeness is not established.",
        ],
    }
    (out / f"{key}-discovery.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("record_type", "counts_as_acquisition_attempt",
          "amc", "official_archive_url", "retrieved_at", "final_url")}, indent=2))
    return 0 if not downloads else 2

if __name__ == "__main__":
    raise SystemExit(main())
