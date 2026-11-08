#!/usr/bin/env python3
"""Bounded NSE bhavcopy ZIP ingestion for explicit, source-backed trade dates.

No weekday/calendar inference is performed. The caller must supply a reviewed
calendar manifest; this worker downloads the full market file, validates it,
and writes immutable raw ZIP plus normalized OHLCV/ISIN rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import time
import zipfile
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = "https://archives.nseindia.com/content/historical/EQUITIES"
UDIFF_ROOT = "https://nsearchives.nseindia.com/content/cm"
USER_AGENT = "Trader-Nifty50-Pilot-Archive-Probe/1.0 (research access check)"
TIMEOUT_SECONDS = 30
MAX_BYTES = 30 * 1024 * 1024
CANONICAL_FIELDS = [
    "trade_date", "symbol", "series", "isin", "open", "high", "low",
    "close", "previous_close", "volume", "turnover",
]


def bhavcopy_url(trade_date: str) -> str:
    day = date.fromisoformat(trade_date)
    if day < date(2024, 7, 8):
        month = day.strftime("%b").upper()
        return (f"{LEGACY_ROOT}/{day.year}/{month}/"
                f"cm{day.day:02d}{month}{day.year}bhav.csv.zip")
    return (f"{UDIFF_ROOT}/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip")



def fetch_bhavcopy(url: str) -> tuple[bytes, int]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = int(response.status)
                payload = response.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise ValueError("bhavcopy download exceeds 30 MiB")
            if status != 200:
                raise ValueError(f"unexpected bhavcopy HTTP status {status}")
            return payload, status
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == 2:
                raise
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"bhavcopy request failed after retries: {last_error}")


def _header_map(headers: list[str]) -> dict[str, str]:
    normalized = {re.sub(r"[^a-z0-9]", "", h.lower()): h for h in headers}
    aliases = {
        "symbol": ("symbol", "tradingsymbol", "tckrsymb"),
        "series": ("series", "sctysrs"),
        "isin": ("isin", "isinno", "isincode"),
        "open": ("open", "opnpric"),
        "high": ("high", "hghpric"),
        "low": ("low", "lwpric"),
        "close": ("close", "clspric"),
        "previous_close": ("prevclose", "previousclose", "prvsclsgpric"),
        "volume": ("tottrdqty", "totaltradedquantity", "ttltradgvol"),
        "turnover": ("tottrdval", "totaltradedvalue", "ttltrfval"),
        "trade_date": ("timestamp", "date1", "trddt", "traddt"),
    }
    mapped = {}
    for key, names in aliases.items():
        found = next((normalized[name] for name in names if name in normalized), None)
        if found:
            mapped[key] = found
    required = set(CANONICAL_FIELDS)
    missing = required - set(mapped)
    if missing:
        raise ValueError(f"bhavcopy CSV is missing required OHLCV/ISIN fields: {sorted(missing)}")
    return mapped


def _parse_date(value: str) -> date:
    token = str(value).strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(token).date()
    except ValueError as exc:
        raise ValueError(f"unrecognized bhavcopy date: {value!r}") from exc


def parse_bhavcopy_zip(payload: bytes, expected_date: str) -> tuple[str, list[dict]]:
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("bhavcopy ZIP is empty or exceeds 30 MiB")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP CRC failure in {bad}")
        csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_members) != 1:
            raise ValueError(f"expected one CSV member, found {len(csv_members)}")
        name = csv_members[0]
        raw = archive.read(name)
    text = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("bhavcopy CSV encoding is unsupported")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("bhavcopy CSV has no header")
    mapping = _header_map(reader.fieldnames)
    rows = []
    for row in reader:
        symbol = str(row.get(mapping["symbol"]) or "").strip().upper()
        series = str(row.get(mapping["series"]) or "").strip().upper()
        isin = str(row.get(mapping["isin"]) or "").strip().upper()
        if not symbol or series != "EQ":
            continue
        row_date = _parse_date(row.get(mapping["trade_date"], ""))
        if row_date.isoformat() != expected_date:
            raise ValueError(f"bhavcopy date mismatch: expected {expected_date}, got {row_date}")
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
            raise ValueError(f"invalid/missing ISIN for {symbol}: {isin!r}")
        record = {"trade_date": expected_date, "symbol": symbol, "series": series, "isin": isin}
        for field in ("open", "high", "low", "close", "previous_close", "volume", "turnover"):
            raw_value = str(row.get(mapping[field]) or "").strip().replace(",", "")
            try:
                value = float(raw_value)
            except ValueError as exc:
                raise ValueError(f"invalid {field} for {symbol}: {raw_value!r}") from exc
            if value < 0:
                raise ValueError(f"negative {field} for {symbol}")
            record[field] = value
        if record["high"] < max(record["open"], record["low"], record["close"]):
            raise ValueError(f"inconsistent high for {symbol}")
        if record["low"] > min(record["open"], record["high"], record["close"]):
            raise ValueError(f"inconsistent low for {symbol}")
        rows.append(record)
    if not rows:
        raise ValueError("bhavcopy contains no EQ rows")
    symbols = [row["symbol"] for row in rows]
    if len(symbols) != len(set(symbols)):
        raise ValueError("bhavcopy contains duplicate EQ symbols")
    return name, rows


def load_calendar_manifest(path: Path, *, allow_candidate_calendar: bool = False) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    required = {"trade_date", "calendar_source_url", "calendar_source_path", "calendar_source_sha256", "calendar_review_status"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"calendar manifest requires columns: {sorted(required)}")
    seen = set()
    for row in rows:
        day = date.fromisoformat(row["trade_date"])
        if day.isoformat() in seen:
            raise ValueError(f"duplicate trade date: {day}")
        seen.add(day.isoformat())
        source_path = (ROOT / row["calendar_source_path"]).resolve()
        source_path.relative_to(ROOT.resolve())
        if not source_path.is_file():
            raise ValueError(f"calendar source file missing: {row['calendar_source_path']}")
        actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if actual != row["calendar_source_sha256"].lower():
            raise ValueError(f"calendar source SHA-256 mismatch: {row['calendar_source_path']}")
        if not row["calendar_source_url"].startswith("https://"):
            raise ValueError(f"calendar source URL must be HTTPS for {day}")
        if row["calendar_review_status"] != "HUMAN_REVIEWED" and not allow_candidate_calendar:
            raise ValueError(f"calendar date {day} is not human-reviewed; pass --allow-candidate-calendar only for isolated research acquisition")
    return sorted(rows, key=lambda row: row["trade_date"])


def acquire(manifest: list[dict], output_dir: Path) -> dict:
    raw_dir = output_dir / "raw"
    parsed_dir = output_dir / "parsed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    results, failures = [], []
    for index, item in enumerate(manifest):
        day = item["trade_date"]
        url = bhavcopy_url(day)
        try:
            payload, http_status = fetch_bhavcopy(url)
            sha = hashlib.sha256(payload).hexdigest()
            member, rows = parse_bhavcopy_zip(payload, day)
            raw_path = raw_dir / f"{day}_{sha}.zip"
            if not raw_path.exists():
                raw_path.write_bytes(payload)
            parsed_path = parsed_dir / f"{day}.csv"
            with parsed_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            results.append({
                "trade_date": day, "url": url, "http_status": http_status,
                "sha256": sha, "bytes_received": len(payload), "zip_member": member,
                "eq_rows": len(rows), "distinct_symbols": len({r["symbol"] for r in rows}),
                "raw_path": raw_path.resolve().relative_to(ROOT.resolve()).as_posix(),
                "parsed_path": parsed_path.resolve().relative_to(ROOT.resolve()).as_posix(),
                "calendar_source_url": item["calendar_source_url"],
                "calendar_source_path": item["calendar_source_path"],
                "calendar_source_sha256": item["calendar_source_sha256"],
                "calendar_review_status": item["calendar_review_status"],
                "status": "DOWNLOADED_AND_VALIDATED",
            })
        except Exception as exc:
            failures.append({"trade_date": day, "url": url,
                             "error": f"{type(exc).__name__}: {exc}"})
        if index < len(manifest) - 1:
            time.sleep(3)
    report = {
        "schema_version": 1,
        "report_type": "NSE_BHAVCOPY_ACQUISITION",
        "status": "COMPLETE" if not failures and len(results) == len(manifest) else "INCOMPLETE",
        "calendar_manifest_rows": len(manifest),
        "downloaded_dates": len(results),
        "failed_dates": failures,
        "records": results,
        "limitations": [
            "Only explicitly supplied, source-hashed calendar dates are attempted; weekdays are not inferred as sessions.",
            "This acquires the full NSE cash-market bhavcopy, not a NIFTY 50-only panel.",
            "ISIN and OHLCV rows are raw-source observations; corporate-action adjustment and membership matching are separate.",
            "Confirm NSE data licence and repository retention permissions before committing raw files.",
        ],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/reference/nse_bhavcopy_2018_2024")
    parser.add_argument("--report", type=Path, default=ROOT / "data/reports/nse_bhavcopy_acquisition.json")
    parser.add_argument("--allow-candidate-calendar", action="store_true",
                        help="allow isolated research acquisition from an unreviewed candidate session list")
    args = parser.parse_args()
    manifest = load_calendar_manifest(args.calendar_manifest,
                                      allow_candidate_calendar=args.allow_candidate_calendar)
    report = acquire(manifest, args.output_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "downloaded_dates": report["downloaded_dates"],
                      "failed_dates": len(report["failed_dates"]), "report": args.report.as_posix()}, indent=2))
    return 0 if report["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
