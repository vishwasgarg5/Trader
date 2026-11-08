"""Acquire the official Nifty Indices NIFTY 50 Total Returns Index series.

The endpoint is an undocumented JSON service exposed by the official NSE Indices
historical-data page. This script preserves the exact HTTP response bytes and
writes a separately normalized CSV. Acquisition is NOT independent verification.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_PAGE = "https://www.niftyindices.com/reports/historical-data"
SOURCE_ENDPOINT = "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString"
START_DATE = date(2018, 1, 1)
END_DATE = date(2024, 12, 31)
USER_AGENT = "Trader-NIFTY50-research-evidence/1.0 (automated official-source acquisition)"
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
RAW_PATH = Path("data/reference/source_documents/nifty50_tri_2018-2024_official_response.json")
CSV_PATH = Path("data/reference/nifty50_tri.csv")
META_PATH = Path("data/reports/nifty50_tri_acquisition.json")
CSV_FIELDS = [
    "session_date", "tri_close", "source_url", "source_published_at",
    "evidence_path", "evidence_sha256", "verification_status", "reviewer", "reviewed_at",
]


def _date_value(value: object) -> date:
    text = str(value or "").strip()
    for fmt in ("%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognized source date: {text!r}")


def _find_field(row: dict, candidates: tuple[str, ...]) -> object | None:
    normalized = {str(key).strip().lower().replace("_", "").replace(" ", ""): value
                  for key, value in row.items()}
    for candidate in candidates:
        key = candidate.lower().replace("_", "").replace(" ", "")
        if key in normalized:
            return normalized[key]
    return None


def parse_response(payload: bytes) -> list[tuple[date, float]]:
    outer = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(outer, dict) or "d" not in outer:
        raise ValueError("official response has no expected ASP.NET 'd' payload")
    inner = outer["d"]
    rows = json.loads(inner) if isinstance(inner, str) else inner
    if not isinstance(rows, list) or not rows:
        raise ValueError("official TRI response contains no observations")

    parsed: list[tuple[date, float]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"source row {index} is not an object")
        index_name = _find_field(row, ("indexName", "IndexName", "name"))
        if index_name is not None and str(index_name).strip().upper().replace(" ", "") != "NIFTY50":
            raise ValueError(f"unexpected index identity in row {index}: {index_name!r}")
        raw_date = _find_field(row, ("HistoricalDate", "Date", "IndexDate"))
        raw_value = _find_field(row, (
            "Total Returns Index", "TotalReturnsIndex", "TRI", "triValue",
            "TotalReturnIndexValue",
        ))
        if raw_date is None or raw_value is None:
            raise ValueError(f"source row {index} lacks date or Total Returns Index field")
        session = _date_value(raw_date)
        try:
            value = float(str(raw_value).replace(",", "").strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"source row {index} has invalid TRI value") from exc
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"source row {index} has non-positive/non-finite TRI")
        if START_DATE <= session <= END_DATE:
            parsed.append((session, value))

    if not parsed:
        raise ValueError("no NIFTY 50 TRI observations fall inside requested date range")
    parsed.sort(key=lambda item: item[0])
    dates = [item[0] for item in parsed]
    if len(dates) != len(set(dates)):
        raise ValueError("duplicate TRI session dates returned by official source")
    if dates[0] > START_DATE or dates[-1] < date(2024, 12, 31):
        raise ValueError(
            f"source coverage does not span requested window: {dates[0]} to {dates[-1]}"
        )
    return parsed


def fetch() -> tuple[bytes, list[tuple[date, float]]]:
    # The cinfo string shape is the request convention used by the official page.
    cinfo = (
        "{'name':'NIFTY 50','startDate':'01-Jan-2018',"
        "'endDate':'31-Dec-2024','indexName':'NIFTY 50'}"
    )
    body = json.dumps({"cinfo": cinfo}).encode("utf-8")
    request = urllib.request.Request(
        SOURCE_ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": SOURCE_PAGE,
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"official TRI endpoint returned HTTP {response.status}")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise RuntimeError("official TRI response exceeds 20 MiB safety limit")
    rows = parse_response(payload)
    return payload, rows


def main() -> int:
    retrieved = datetime.now(timezone.utc)
    ist = retrieved.astimezone(ZoneInfo("Asia/Kolkata"))
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "source_page": SOURCE_PAGE,
        "source_endpoint": SOURCE_ENDPOINT,
        "source_owner": "NSE Indices",
        "index": "NIFTY 50",
        "series": "Total Returns Index",
        "explicitly_excluded_series": ["Net Total Return Index", "price-return index"],
        "requested_start": START_DATE.isoformat(),
        "requested_end": END_DATE.isoformat(),
        "retrieved_at_utc": retrieved.isoformat(),
        "retrieved_at_ist": ist.isoformat(),
        "status": "ACQUISITION_FAILED",
        "independent_verification": "PENDING",
        "reviewer": None,
        "holdout_access_authorized": False,
    }
    try:
        payload, rows = fetch()
        digest = hashlib.sha256(payload).hexdigest()
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        META_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_PATH.write_bytes(payload)
        with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for session, value in rows:
                writer.writerow({
                    "session_date": session.isoformat(),
                    "tri_close": format(value, ".10g"),
                    "source_url": SOURCE_ENDPOINT,
                    "source_published_at": "",
                    "evidence_path": RAW_PATH.as_posix(),
                    "evidence_sha256": digest,
                    "verification_status": "ACQUIRED_PENDING_INDEPENDENT_REVIEW",
                    "reviewer": "",
                    "reviewed_at": "",
                })
        report.update({
            "status": "ACQUIRED_PENDING_CALENDAR_AND_INDEPENDENT_REVIEW",
            "record_count": len(rows),
            "first_session": rows[0][0].isoformat(),
            "last_session": rows[-1][0].isoformat(),
            "raw_response_path": RAW_PATH.as_posix(),
            "normalized_csv_path": CSV_PATH.as_posix(),
            "raw_response_bytes": len(payload),
            "raw_response_sha256": digest,
            "normalization": "Date + Total Returns Index only; Net TRI and price index excluded",
            "calendar_completeness": "NOT_YET_VERIFIED",
            "source_authenticity_review": "PENDING",
        })
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(report, indent=2, sort_keys=True))
        META_PATH.parent.mkdir(parents=True, exist_ok=True)
        META_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 1

    META_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
