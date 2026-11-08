#!/usr/bin/env python3
"""Cross-check one official Nippon Nifty 50 portfolio against NSE bhavcopy.

This is corroboration only. It never changes the canonical membership ledger.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import requests
import xlrd

from scripts.build_nifty50_anchor_matching_packet import (
    load_transition_rows, load_verified_anchors,
)
from scripts.acquire_nse_bhavcopy import bhavcopy_url, fetch_bhavcopy, parse_bhavcopy_zip

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data/reference/wayback_nifty50_acquisition_state.json"
TRANSITIONS_PATH = ROOT / "data/reference/nifty50_transition_register.csv"
REPORT_PATH = ROOT / "data/reports/nippon_nifty50_2024q4_crosscheck.json"
WORKBOOK_URL = "https://mf.nipponindiaim.com/InvestorServices/FactsheetsDocuments/NIMF-MONTHLY-PORTFOLIO-31-Dec-24.xls"
AS_OF_DATE = "2024-12-31"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
USER_AGENT = "Trader-NIFTY50-AMC-Crosscheck/1.0 (+https://github.com/vishwasgarg5/Trader)"


def parse_nippon_nifty50_holdings(payload: bytes) -> list[dict]:
    if not payload.startswith(OLE_MAGIC):
        raise ValueError("Nippon source is not an OLE .xls workbook")
    book = xlrd.open_workbook(file_contents=payload, on_demand=False)
    index_sheet = book.sheet_by_name("INDEX")
    scheme_code = None
    for row in range(index_sheet.nrows):
        code = str(index_sheet.cell_value(row, 0)).strip()
        name = str(index_sheet.cell_value(row, 1)).strip().upper()
        if "NIPPON INDIA INDEX FUND - NIFTY 50 PLAN" in name:
            scheme_code = code
            break
    if not scheme_code:
        raise ValueError("INDEX sheet does not identify Nippon India Index Fund - Nifty 50 Plan")
    sheet = book.sheet_by_name(scheme_code)
    header_row = None
    for row in range(sheet.nrows):
        values = [str(sheet.cell_value(row, col)).strip().casefold() for col in range(sheet.ncols)]
        if "isin" in values and "name of the instrument" in values:
            header_row = row
            break
    if header_row is None:
        raise ValueError("Nifty 50 scheme sheet has no ISIN / instrument-name header")
    holdings = []
    for row in range(header_row + 1, sheet.nrows):
        values = [sheet.cell_value(row, col) for col in range(sheet.ncols)]
        isin = str(values[1]).strip().upper()
        name = str(values[2]).strip()
        if not ISIN_RE.fullmatch(isin) or not name:
            continue
        holdings.append({
            "isin": isin,
            "security_name": name,
            "quantity": float(values[4]) if str(values[4]).strip() else None,
            "market_value_lakh": float(values[5]) if str(values[5]).strip() else None,
            "weight_fraction_nav": float(values[6]) if str(values[6]).strip() else None,
        })
    if len(holdings) != 50 or len({x["isin"] for x in holdings}) != 50:
        raise ValueError(f"expected 50 distinct equity ISINs, found {len(holdings)}")
    return holdings


def map_isins_to_symbols(holdings: list[dict], bhav_rows: list[dict]) -> tuple[list[dict], list[str]]:
    mapping = {}
    for row in bhav_rows:
        if row.get("series") != "EQ":
            continue
        isin, symbol = row.get("isin", "").upper(), row.get("symbol", "").upper()
        if not ISIN_RE.fullmatch(isin) or not symbol:
            continue
        if isin in mapping and mapping[isin] != symbol:
            raise ValueError(f"one ISIN maps to multiple EQ symbols: {isin}")
        mapping[isin] = symbol
    mapped, missing = [], []
    for holding in holdings:
        symbol = mapping.get(holding["isin"])
        if not symbol:
            missing.append(holding["isin"])
        else:
            mapped.append({**holding, "symbol": symbol})
    return mapped, missing


def main() -> int:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    workbook_response = session.get(WORKBOOK_URL, timeout=(20, 90))
    workbook_response.raise_for_status()
    workbook_bytes = workbook_response.content
    workbook_sha = hashlib.sha256(workbook_bytes).hexdigest()
    holdings = parse_nippon_nifty50_holdings(workbook_bytes)

    bhav_url = bhavcopy_url(AS_OF_DATE)
    # Reuse the bounded retrying downloader used by the NSE ingestion workflow.
    # NSE archive read timeouts are transient; never substitute unverified data.
    bhav_bytes, bhav_http_status = fetch_bhavcopy(bhav_url)
    bhav_sha = hashlib.sha256(bhav_bytes).hexdigest()
    bhav_member, bhav_rows = parse_bhavcopy_zip(bhav_bytes, AS_OF_DATE)
    mapped, missing_isins = map_isins_to_symbols(holdings, bhav_rows)

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    anchors, rejected = load_verified_anchors(state, ROOT)
    anchor = next((x for x in anchors if x["quarter"] == "2024-Q4"), None)
    if not anchor:
        raise ValueError("no CDX-verified 2024-Q4 Wayback anchor found")
    nippon_symbols = sorted({x["symbol"] for x in mapped})
    anchor_symbols = sorted(set(anchor["symbols"]))
    only_in_nippon = sorted(set(nippon_symbols) - set(anchor_symbols))
    only_in_wayback = sorted(set(anchor_symbols) - set(nippon_symbols))

    transition_rows = load_transition_rows(TRANSITIONS_PATH)
    start = date.fromisoformat(anchor["as_of_date"])
    end = date.fromisoformat(AS_OF_DATE)
    events = []
    for event in transition_rows:
        try:
            effective = date.fromisoformat(event.get("effective_date", "").strip())
        except ValueError:
            continue
        if start < effective <= end:
            events.append({
                "transition_id": event.get("transition_id", ""),
                "symbol": event.get("symbol", "").strip().upper(),
                "action": event.get("action", "").strip().upper(),
                "effective_date": event.get("effective_date", ""),
                "verification_status": event.get("verification_status", ""),
                "source_url": event.get("source_url", ""),
                "source_document_path": event.get("source_document_path", ""),
            })

    matched = not missing_isins and not only_in_nippon and not only_in_wayback
    report = {
        "schema_version": 1,
        "report_type": "NIPPON_NIFTY50_VS_WAYBACK_AND_NSE_BHAVCOPY_CROSSCHECK",
        "status": "MATCH_CANDIDATE_PENDING_HUMAN_REVIEW" if matched else "DIFFERENCES_REQUIRE_REVIEW",
        "scope": "NIFTY 50 pilot only",
        "fund_source": {
            "url": WORKBOOK_URL, "as_of_date": AS_OF_DATE,
            "publication_date": None,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "http_status": workbook_response.status_code,
            "content_type": workbook_response.headers.get("Content-Type"),
            "sha256": workbook_sha,
            "holdings_count": len(holdings),
            "distinct_isin_count": len({x["isin"] for x in holdings}),
            "holdings": mapped,
        },
        "bhavcopy_source": {
            "url": bhav_url, "trade_date": AS_OF_DATE,
            "http_status": bhav_http_status,
            "sha256": bhav_sha, "zip_member": bhav_member,
            "eq_rows": len(bhav_rows), "distinct_eq_isins": len({x["isin"] for x in bhav_rows}),
        },
        "wayback_anchor": {
            "quarter": anchor["quarter"], "as_of_date": anchor["as_of_date"],
            "capture_timestamp": anchor["timestamp"], "sha256": anchor["sha256"],
            "cdx_digest": anchor["cdx_digest"], "review_status": anchor["review_status"],
        },
        "comparison": {
            "mapped_holdings": len(mapped), "unmapped_isins": missing_isins,
            "nifty50_symbols_from_fund_isins": nippon_symbols,
            "wayback_anchor_symbols": anchor_symbols,
            "only_in_fund_portfolio": only_in_nippon,
            "only_in_wayback_anchor": only_in_wayback,
            "registered_transition_events_between_dates": events,
        },
        "rejected_wayback_candidates": rejected,
        "limitations": [
            "The fund portfolio is corroborative evidence, not a direct index constituent record.",
            "The portfolio as-of date and publication date are distinct; publication date was not established by this probe.",
            "The Wayback anchor remains a candidate pending human review.",
            "Transition register statuses are copied unchanged; SAMPLE_ONLY is not upgraded.",
            "No canonical membership interval or model input is written.",
            "No model validation, holdout, paper-trading or live-trading permission is enabled.",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "fund_holdings": len(holdings),
        "mapped": len(mapped), "unmapped_isins": len(missing_isins),
        "only_in_fund": only_in_nippon, "only_in_wayback": only_in_wayback,
        "registered_events": len(events), "report": REPORT_PATH.as_posix(),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
