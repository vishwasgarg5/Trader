#!/usr/bin/env python3
"""Re-fetch NIFTY 50 gross TRI through the NSE Indices historical-data UI route.

This is a second capture through the official report-page endpoint. It is a
reproducibility cross-check, not an independent publisher/source review.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

SOURCE_PAGE = "https://www.niftyindices.com/reports/historical-data"
ENDPOINT = "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString"
TRI_CSV = Path("data/reference/nifty50_tri.csv")
RAW_DIR = Path("data/reference/source_documents/nifty50_tri_ui_export")
REPORT = Path("data/reports/nifty50_tri_ui_export_reconciliation.json")
START = date(2018, 1, 1)
END = date(2024, 12, 31)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 TraderResearch/1.0")


def windows():
    # One native UI export for the full pilot window avoids repeated requests.
    yield START, END


def fetch(start: date, end: date) -> bytes:
    inner = (
        f"{{'name':'NIFTY 50','startDate':'{start:%d-%b-%Y}',"
        f"'endDate':'{end:%d-%b-%Y}','indexName':'NIFTY 50'}}"
    )
    payload = json.dumps({"cinfo": inner}).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": SOURCE_PAGE,
        "Origin": "https://www.niftyindices.com",
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
    }, method="POST")
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                body = response.read(20 * 1024 * 1024 + 1)
                if response.status != 200 or len(body) > 20 * 1024 * 1024:
                    raise RuntimeError(f"unexpected HTTP/response size: {response.status}/{len(body)}")
                outer = json.loads(body.decode("utf-8-sig"))
                rows = json.loads(outer["d"]) if isinstance(outer.get("d"), str) else outer.get("d")
                if not isinstance(rows, list) or not rows:
                    raise ValueError("NSE UI endpoint returned no rows")
                return body
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}: {exc.read(300).decode(errors='replace')}"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        if attempt < 1:
            time.sleep(2)
    raise RuntimeError(last or "request failed")


def parse(body: bytes, start: date, end: date) -> dict[date, Decimal]:
    outer = json.loads(body.decode("utf-8-sig"))
    rows = json.loads(outer["d"]) if isinstance(outer.get("d"), str) else outer.get("d")
    result = {}
    for i, row in enumerate(rows, 1):
        name = str(row.get("Index Name", row.get("indexName", ""))).strip().upper().replace(" ", "")
        if name != "NIFTY50":
            raise ValueError(f"row {i}: unexpected index {name!r}")
        date_text = row.get("Date", row.get("HistoricalDate"))
        value = row.get("TotalReturnsIndex", row.get("Total Returns Index"))
        if date_text is None or value is None:
            raise ValueError(f"row {i}: missing Date or TotalReturnsIndex")
        day = date.strptime(date_text, "%d %b %Y") if hasattr(date, "strptime") else None
        if day is None:
            from datetime import datetime
            day = datetime.strptime(date_text, "%d %b %Y").date()
        if start <= day <= end:
            try:
                result[day] = Decimal(str(value).replace(",", "").strip())
            except InvalidOperation as exc:
                raise ValueError(f"row {i}: invalid TRI value {value!r}") from exc
    if not result:
        raise ValueError(f"no observations in {start}..{end}")
    if len(result) != len([d for d in result]):
        raise ValueError("duplicate dates in UI export")
    return result


def main() -> int:
    expected = {}
    with TRI_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            expected[date.fromisoformat(row["session_date"])] = Decimal(row["tri_close"])
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    chunks, observed = [], {}
    failures = []
    for start, end in windows():
        path = RAW_DIR / f"nifty50_tri_ui_{start.isoformat()}_{end.isoformat()}.json"
        try:
            body = fetch(start, end)
            path.write_bytes(body)
            parsed = parse(body, start, end)
            observed.update(parsed)
            chunks.append({
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "raw_path": path.as_posix(),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "row_count": len(parsed),
                "first_date": min(parsed).isoformat(),
                "last_date": max(parsed).isoformat(),
                "status": "CAPTURED",
            })
        except Exception as exc:
            failures.append({
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "error": str(exc),
                "status": "FAILED",
            })
        time.sleep(1)
    missing = sorted(d.isoformat() for d in set(expected) - set(observed))
    extra = sorted(d.isoformat() for d in set(observed) - set(expected))
    mismatches = [
        {"date": d.isoformat(), "acquired": str(expected[d]), "ui_export": str(observed[d])}
        for d in sorted(set(expected) & set(observed)) if expected[d] != observed[d]
    ]
    exact = not failures and not missing and not extra and not mismatches and len(observed) == len(expected)
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "source_page": SOURCE_PAGE,
        "source_endpoint": ENDPOINT,
        "series": "NIFTY 50 gross Total Returns Index",
        "range": {"start": START.isoformat(), "end": END.isoformat()},
        "acquired_row_count": len(expected),
        "ui_export_row_count": len(observed),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "failures": failures,
        "missing_dates_in_ui_export": missing,
        "extra_dates_in_ui_export": extra,
        "value_mismatches": mismatches,
        "cross_capture_result": "EXACT_MATCH" if exact else "NOT_RECONCILED",
        "source_independence": "NOT_INDEPENDENT_SAME_NSE_INDICES_PUBLISHER_AND_UNDOCUMENTED_ENDPOINT_FAMILY",
        "independent_reviewer": None,
        "independent_reviewer_signoff": "PENDING",
        "source_authenticity": "PENDING_INDEPENDENT_REVIEW",
        "interpretation": (
            "A second capture via the NSE Indices historical-data page route tests reproducibility "
            "and row/value consistency only. It is not an independent source or reviewer sign-off."
        ),
        "research_status": "RESEARCH_HOLD",
        "holdout_access_authorized": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "acquired_row_count": len(expected),
        "ui_export_row_count": len(observed),
        "cross_capture_result": report["cross_capture_result"],
        "failures": failures,
        "missing_dates": len(missing),
        "extra_dates": len(extra),
        "value_mismatches": len(mismatches),
    }, indent=2))
    return 0 if exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
