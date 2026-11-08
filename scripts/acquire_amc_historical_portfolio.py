#!/usr/bin/env python3
"""One-shot corrected-design Motilal Oswal December 2024 portfolio acquisition.

Downloads are permitted only from exact hrefs observed on the live official AMC
DOM. No filenames or download URLs are constructed. This script is one attempt:
MOTILAL_CORRECTED_DESIGN_ATTEMPT_003 (two earlier attempts were consumed).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from playwright.sync_api import sync_playwright

BASE = "https://www.motilaloswalmf.com"
ARCHIVE = BASE + "/downloads/scheme-portfolio-details"
SCHEME_PAGE = BASE + "/mutual-funds/motilal-oswal-nifty-50-index-fund"
OUT = Path("acquisition-output")
OUT.mkdir(exist_ok=True)
ATTEMPT_ID = "MOTILAL_CORRECTED_DESIGN_ATTEMPT_003"
OFFICIAL_HOST = "motilaloswalmf.com"
MONTHLY_RE = re.compile(
    r"(?:december|dec)[\s,./_-]*(?:2024|24)|2024[-_/]12|31[-_/]12[-_/]2024|12[-_/]2024",
    re.I,
)
FORTNIGHTLY_RE = re.compile(
    r"(?:15(?:th)?[\s,./_-]*(?:december|dec|12)[\s,./_-]*2024|15[-_/]12[-_/]2024|2024[-_/]12[-_/]15)",
    re.I,
)
ISIN_RE = re.compile(r"^INE[A-Z0-9]{9}$", re.I)

events: list[dict] = []
discovered_links: list[dict] = []
downloads: list[dict] = []
errors: list[dict] = []


def official_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == OFFICIAL_HOST or host.endswith("." + OFFICIAL_HOST)


def record_page(page, requested_url: str) -> None:
    if not official_host(page.url):
        events.append({"page_error": requested_url, "error": "Page redirected outside official AMC domain", "final_url": page.url})
        return
    events.append({
        "page": requested_url,
        "final_url": page.url,
        "title": page.title(),
        "body_excerpt": re.sub(r"\s+", " ", page.locator("body").inner_text())[:8000],
        "controls": page.locator("select").evaluate_all(
            """els => els.map((e, i) => ({
                index: i, name: e.name || null, id: e.id || null,
                aria_label: e.getAttribute('aria-label'),
                label: e.labels ? Array.from(e.labels).map(x => x.innerText.trim()).join(' ') : '',
                options: Array.from(e.options).map(o => ({text:o.text.trim(), value:o.value}))
            }))"""
        ),
    })


def choose_date_and_scheme_options(page) -> None:
    """Use only visible official-page select options, never synthesize file URLs."""
    selects = page.locator("select")
    for index in range(selects.count()):
        select = selects.nth(index)
        try:
            if not select.is_visible():
                continue
            metadata = select.evaluate("""e => ({
                name: (e.name || '').toLowerCase(),
                id: (e.id || '').toLowerCase(),
                aria: (e.getAttribute('aria-label') || '').toLowerCase(),
                label: e.labels ? Array.from(e.labels).map(x => x.innerText).join(' ').toLowerCase() : ''
            })""")
            label = " ".join(metadata.values())
            options = select.locator("option").evaluate_all(
                "(els) => els.map(e => ({text:(e.textContent||'').trim(), value:e.value}))"
            )
            chosen = None
            if "scheme" in label or "fund" in label:
                chosen = next((o for o in options if "motilal oswal nifty 50 index fund" in o["text"].lower() and o["value"]), None)
            elif "month" in label:
                chosen = next((o for o in options if o["text"].strip().lower() in ("december", "dec") and o["value"]), None)
            elif "year" in label:
                chosen = next((o for o in options if o["text"].strip() == "2024" and o["value"]), None)
            else:
                chosen = next((o for o in options if MONTHLY_RE.search(o["text"]) and o["value"]), None)
            if chosen:
                select.select_option(chosen["value"], timeout=7000)
                page.wait_for_timeout(1800)
                events.append({"select_changed": index, "label": label, "selected_text": chosen["text"]})
        except Exception as exc:
            errors.append({"select_error": str(exc), "index": index})


def collect_dom_links(page, requested_url: str) -> None:
    if not official_host(page.url):
        return
    rows = page.locator("a[href]").evaluate_all(
        """els => els.map((a, index) => {
            const row = a.closest('tr, li, article, [class*=document], [class*=portfolio], [class*=result], .card') || a.parentElement;
            return {
                index,
                text: (a.innerText || a.getAttribute('aria-label') || '').trim(),
                href: a.getAttribute('href'),
                row_text: row ? (row.innerText || '').trim().slice(0, 1600) : ''
            };
        })"""
    )
    for item in rows:
        href = (item.get("href") or "").strip()
        if not href or href.startswith("#") or href.lower().startswith(("javascript:", "mailto:", "tel:")):
            continue
        exact_url = urljoin(page.url, href)
        # Retain only links whose actual visible row/text describes the requested
        # scheme and a requested December 2024 portfolio date.
        context = " ".join((item.get("text") or "", item.get("row_text") or ""))
        low = context.lower()
        if "nifty 50" not in low or "index fund" not in low:
            continue
        monthly = bool(MONTHLY_RE.search(context))
        fortnightly = bool(FORTNIGHTLY_RE.search(context))
        if not (monthly or fortnightly):
            continue
        if not official_host(exact_url):
            events.append({"rejected_dom_link": exact_url, "reason": "Link is outside official AMC domain", "context": context})
            continue
        discovered_links.append({
            "discovered_on_page": page.url,
            "requested_page": requested_url,
            "anchor_text": item.get("text"),
            "row_context": context,
            "source_url": exact_url,
            "target_type": "fortnightly_2024-12-15" if fortnightly else "monthly_2024-12",
        })


def parse_equity_isins(path: Path) -> dict:
    """Extract ISIN-level rows reproducibly from workbook sheets and header rows."""
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    extracted: dict[str, dict] = {}
    sheet_diagnostics = []
    for sheet in workbook.worksheets:
        header_found = False
        max_header_scan = min(sheet.max_row or 0, 40)
        for row_number in range(1, max_header_scan + 1):
            values = next(sheet.iter_rows(min_row=row_number, max_row=row_number, values_only=True))
            headers = [str(v).strip() if v is not None else "" for v in values]
            isin_columns = [i for i, value in enumerate(headers) if "isin" in value.lower()]
            if not isin_columns:
                continue
            isin_col = isin_columns[0]
            asset_cols = [
                i for i, value in enumerate(headers)
                if any(term in value.lower() for term in ("asset class", "instrument type", "security type", "classification"))
            ]
            name_cols = [
                i for i, value in enumerate(headers)
                if any(term in value.lower() for term in ("name of instrument", "instrument name", "security name", "name of security", "company"))
            ]
            accepted_here = 0
            for row_idx, row in enumerate(sheet.iter_rows(min_row=row_number + 1, values_only=True), start=row_number + 1):
                if isin_col >= len(row) or row[isin_col] is None:
                    continue
                isin = re.sub(r"\s+", "", str(row[isin_col])).upper()
                if not ISIN_RE.fullmatch(isin):
                    continue
                asset_value = " ".join(str(row[i]) for i in asset_cols if i < len(row) and row[i] is not None).lower()
                if asset_cols and "equity" not in asset_value:
                    continue
                name = " ".join(str(row[i]).strip() for i in name_cols if i < len(row) and row[i] is not None)
                extracted[isin] = {
                    "isin": isin,
                    "security_name": name or None,
                    "sheet": sheet.title,
                    "row_number": row_idx,
                    "classification": "equity_column" if asset_cols else "INE_ISIN_equity_candidate",
                    "row_values": [str(v) if v is not None else None for v in row],
                    "headers": headers,
                }
                accepted_here += 1
            sheet_diagnostics.append({
                "sheet": sheet.title, "header_row": row_number,
                "isin_column_index": isin_col, "asset_class_column_indices": asset_cols,
                "equity_rows_extracted": accepted_here,
            })
            header_found = True
            break
        if not header_found:
            sheet_diagnostics.append({"sheet": sheet.title, "header_found": False})
    workbook.close()
    return {
        "method": "scan each worksheet's first 40 rows for an ISIN header; accept INE-prefixed 12-character ISINs; if an asset/security/classification column exists require its row value to contain 'equity'; deduplicate by ISIN",
        "equity_isin_count": len(extracted),
        "about_50_check": "PASS" if 40 <= len(extracted) <= 60 else "OUTSIDE_40_TO_60_RANGE",
        "equity_holdings": [extracted[key] for key in sorted(extracted)],
        "sheet_diagnostics": sheet_diagnostics,
    }


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(accept_downloads=False)
        page = context.new_page()
        for url in (ARCHIVE, SCHEME_PAGE):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4500)
                record_page(page, url)
                choose_date_and_scheme_options(page)
                record_page(page, url)
                collect_dom_links(page, url)
            except Exception as exc:
                errors.append({"page_error": url, "error": str(exc), "final_url": page.url})
        browser.close()

    # De-duplicate only identical DOM-discovered URLs. No other URLs are generated.
    unique = {}
    for item in discovered_links:
        unique.setdefault(item["source_url"], item)
    discovered_links[:] = list(unique.values())

    # Prefer one monthly file and optionally one 15-Dec fortnightly file.
    wanted = []
    for kind in ("monthly_2024-12", "fortnightly_2024-12-15"):
        item = next((x for x in discovered_links if x["target_type"] == kind), None)
        if item:
            wanted.append(item)

    for item in wanted:
        try:
            response = context.request.get(item["source_url"], timeout=60000)
            final_url = response.url
            if not official_host(final_url):
                raise ValueError("Download redirected outside official AMC domain")
            if response.status != 200:
                raise ValueError(f"HTTP status {response.status}")
            body = response.body()
            if len(body) < 5000 or body[:2] != b"PK":
                raise ValueError("Discovered link did not return an XLSX ZIP payload")
            # Hash the original response bytes before any workbook parsing.
            digest = hashlib.sha256(body).hexdigest()
            original_name = unquote(urlparse(item["source_url"]).path.rsplit("/", 1)[-1]) or ""
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name).strip("._")
            if not safe_name.lower().endswith(".xlsx"):
                safe_name = "motilal_nifty50_" + item["target_type"] + ".xlsx"
            target = OUT / safe_name
            target.write_bytes(body)
            record = {
                **item,
                "final_response_url": final_url,
                "original_filename_from_link": original_name or None,
                "saved_filename": safe_name,
                "byte_count": len(body),
                "sha256": digest,
                "sha256_recorded_before_parsing": True,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "attempt_id": ATTEMPT_ID,
            }
            # Parse only after the original-byte hash has been recorded.
            parsed = parse_equity_isins(target)
            parsed_path = OUT / (safe_name + ".equity_isins.json")
            parsed_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
            record["equity_isin_file"] = parsed_path.name
            record["equity_isin_count"] = parsed["equity_isin_count"]
            record["about_50_check"] = parsed["about_50_check"]
            downloads.append(record)
        except Exception as exc:
            errors.append({"download_error": str(exc), "source_url": item["source_url"], "target_type": item["target_type"]})

    monthly_acquired = any(x["target_type"] == "monthly_2024-12" for x in downloads)
    status = "ACQUIRED" if monthly_acquired else ("PARTIAL" if downloads else "NOT_ACQUIRED")
    result = {
        "attempt_id": ATTEMPT_ID,
        "attempt_label": "single corrected-design Motilal attempt; separately labelled from two previously consumed attempts",
        "previous_attempts_consumed": 2,
        "this_attempt_number": 3,
        "status": status,
        "monthly_december_2024_acquired": monthly_acquired,
        "fortnightly_2024_12_15_acquired": any(x["target_type"] == "fortnightly_2024-12-15" for x in downloads),
        "downloads": downloads,
        "discovered_eligible_links": discovered_links,
        "errors": errors,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "download_rule": "exact href discovered in live official AMC DOM only; no constructed source URLs or filenames",
        "reconciliation_status": "STEP_2_REMAINS_OPEN_REQUIRES_AT_LEAST_THREE_ELIGIBLE_FUNDS_TO_AGREE",
        "independent_reviewer_status": "NOT_DESIGNATED_FINAL_SIGNOFF_BLOCKED",
    }
    (OUT / "acquisition_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "browser_diagnostics.json").write_text(json.dumps({
        "attempt_id": ATTEMPT_ID,
        "events": events,
        "discovered_eligible_links": discovered_links,
        "errors": errors,
    }, indent=2), encoding="utf-8")
    print(json.dumps({
        "attempt_id": ATTEMPT_ID,
        "status": status,
        "monthly_december_2024_acquired": monthly_acquired,
        "fortnightly_2024_12_15_acquired": result["fortnightly_2024_12_15_acquired"],
        "download_count": len(downloads),
        "errors": errors,
    }, indent=2))
    return 0 if monthly_acquired else 1


if __name__ == "__main__":
    raise SystemExit(main())
