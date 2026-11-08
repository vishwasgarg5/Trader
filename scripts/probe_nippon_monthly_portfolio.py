#!/usr/bin/env python3
"""Probe one official Nippon India monthly portfolio workbook.

This is source/schema discovery only. It does not write membership evidence or
promote any fund holding to an index constituent.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
import xlrd

URL = "https://mf.nipponindiaim.com/InvestorServices/FactsheetsDocuments/NIMF-MONTHLY-PORTFOLIO-31-Dec-24.xls"
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/probes/nippon_monthly_portfolio"
USER_AGENT = "Trader-NIFTY50-Disclosure-Probe/1.0 (+https://github.com/vishwasgarg5/Trader)"
MAX_BYTES = 30 * 1024 * 1024
OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


def inspect_workbook(payload: bytes) -> dict:
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("workbook is empty or exceeds 30 MiB")
    if not payload.startswith(OLE_MAGIC):
        raise ValueError("download is not an OLE .xls workbook")
    book = xlrd.open_workbook(file_contents=payload, on_demand=False)
    sheets = []
    hits = []
    target_scheme_sheets = []
    for sheet in book.sheets():
        preview = []
        for r in range(min(sheet.nrows, 8)):
            preview.append([str(sheet.cell_value(r, c))[:160]
                            for c in range(min(sheet.ncols, 12))])
        sheets.append({"name": sheet.name, "rows": sheet.nrows,
                       "columns": sheet.ncols, "preview": preview})
        if sheet.name == "NF":
            target_scheme_sheets.append({
                "sheet_name": sheet.name,
                "rows": sheet.nrows,
                "columns": sheet.ncols,
                "all_rows": [
                    [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
                    for r in range(sheet.nrows)
                ],
            })
        for r in range(sheet.nrows):
            values = [str(sheet.cell_value(r, c)).strip()
                      for c in range(sheet.ncols)]
            joined = " | ".join(v for v in values if v)
            if "nifty" in joined.casefold():
                hits.append({"sheet": sheet.name, "row_number_1_based": r + 1,
                             "values": values[:24]})
    return {
        "sheet_count": len(sheets),
        "sheets": sheets,
        "target_scheme_sheets": target_scheme_sheets,
        "nifty_keyword_rows": hits[:1000],
        "nifty_keyword_row_count": len(hits),
        "nifty_50_index_fund_scheme_name_found": any(
            "nifty 50" in " ".join(hit["values"]).casefold()
            and ("index fund" in " ".join(hit["values"]).casefold()
                 or "nifty plan" in " ".join(hit["values"]).casefold())
            for hit in hits
        ),
    }


def main() -> int:
    response = requests.get(URL, headers={"User-Agent": USER_AGENT,
        "Accept": "application/vnd.ms-excel,application/octet-stream",
        "Accept-Encoding": "identity"}, timeout=(20, 90))
    response.raise_for_status()
    payload = response.content
    result = inspect_workbook(payload)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = OUT_DIR / "NIMF-MONTHLY-PORTFOLIO-31-Dec-24.xls"
    raw_path.write_bytes(payload)
    report = {
        "report_type": "NIPPON_MONTHLY_PORTFOLIO_SOURCE_PROBE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": URL,
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "content_length_header": response.headers.get("Content-Length"),
        "bytes_received": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "raw_path": raw_path.relative_to(ROOT).as_posix(),
        "as_of_date": "2024-12-31",
        "source_type": "OFFICIAL_AMC_MONTHLY_SCHEME_PORTFOLIO",
        "interpretation": "Holdings are corroborative evidence only; index fund replication may have cash, receivables, sampling and tracking differences.",
        **result,
    }
    report_path = OUT_DIR / "probe_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "report_type", "source_url", "http_status", "content_type",
        "bytes_received", "sha256", "sheet_count",
        "nifty_keyword_row_count", "nifty_50_index_fund_scheme_name_found",
        "raw_path",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
