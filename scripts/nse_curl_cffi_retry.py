#!/usr/bin/env python3
"""Controlled curl_cffi retry for official NSE/Nifty Indices PDFs plus Wayback CDX ingestion.

Only complete, structurally bounded PDF bodies are archived and hashed. This is
source acquisition diagnostics only: it never updates model data or membership.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import pathlib
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

from curl_cffi import requests as c_requests
import requests

INPUT = pathlib.Path("data/reports/weekly_market_document_acquisition.json")
OUTPUT = pathlib.Path("data/reports/nse_curl_cffi_retry.json")
ARCHIVE = pathlib.Path("data/reference/source_documents/nse_curl_cffi_retry")
WAYBACK_OUTPUT = pathlib.Path("data/reports/wayback_cdx_ingestion.json")
WAYBACK_ARCHIVE = pathlib.Path("data/reference/wayback_cdx")
MAX_BYTES = 50 * 1024 * 1024
CONNECT_TIMEOUT = 20
READ_TIMEOUT = 180
ATTEMPTS = 3
BACKOFF_SECONDS = (3, 10)
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.niftyindices.com/reports",
    "Connection": "keep-alive",
}
ALLOWED_HOSTS = {
    "niftyindices.com", "www.niftyindices.com",
    "nseindia.com", "www.nseindia.com", "nsearchives.nseindia.com",
    "archives.nseindia.com",
}
WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_SNAPSHOT_ARCHIVE = pathlib.Path("data/reference/source_documents/wayback_nifty50_snapshots")
SNAPSHOT_CSV_TARGETS = {
    "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://www.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "https://niftyindices.com/IndexConstituent/ind_nifty50list.csv",
}
SNAPSHOT_HISTORY_TARGETS = SNAPSHOT_CSV_TARGETS | {
    "https://www.nseindia.com/content/indices/IndexInclExcl.xls",
    "https://archives.nseindia.com/content/indices/IndexInclExcl.xls",
}
IP_ECHO = "https://api.ipify.org?format=json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowed_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in ALLOWED_HOSTS


def validate_pdf(body: bytes, content_length: str | None = None) -> None:
    if content_length:
        expected = int(content_length)
        if expected != len(body):
            raise ValueError(f"Content-Length mismatch: expected {expected}, received {len(body)}")
    if not body.startswith(b"%PDF"):
        raise ValueError("body does not start with %PDF")
    if not body.rstrip().endswith(b"%%EOF"):
        raise ValueError("body does not end with %%EOF")


def get_egress_ip() -> dict:
    result = {"checked_at_utc": now_utc(), "service": IP_ECHO}
    try:
        with c_requests.Session(impersonate="chrome") as session:
            response = session.get(IP_ECHO, timeout=(CONNECT_TIMEOUT, 20))
            result.update({"http_status": response.status_code, "ip": response.json().get("ip")})
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:500]
    return result


def source_candidates() -> list[dict]:
    report = json.loads(INPUT.read_text(encoding="utf-8"))
    rows = report.get("document_failures", [])
    unique = {}
    for row in rows:
        url = row.get("source_url", "")
        if allowed_url(url):
            unique[url] = {"source_url": url, "source_id": row.get("source_id"),
                           "publisher": row.get("publisher")}
    return [unique[url] for url in sorted(unique)]


def download_one(item: dict) -> dict:
    url = item["source_url"]
    result = {**item, "attempts": [], "retrieved_at_utc": now_utc()}
    if not allowed_url(url):
        result.update({"status": "FAILED_HOST_NOT_ALLOWLISTED", "bytes_received": 0})
        return result
    for attempt in range(1, ATTEMPTS + 1):
        record = {"attempt": attempt, "started_at_utc": now_utc(), "bytes_received": 0}
        try:
            chunks = []
            with c_requests.Session(impersonate="chrome") as session:
                response = session.get(url, headers=HEADERS,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), stream=True,
                    allow_redirects=True)
                record["http_status"] = response.status_code
                record["final_url"] = str(response.url)
                record["content_type"] = response.headers.get("Content-Type")
                record["content_length"] = response.headers.get("Content-Length")
                if not allowed_url(record["final_url"]):
                    raise ValueError("redirect left official NSE/Nifty Indices host allowlist")
                if response.status_code != 200:
                    raise ValueError(f"unexpected HTTP status {response.status_code}")
                for chunk in response.iter_content(64 * 1024):
                    if chunk:
                        record["bytes_received"] += len(chunk)
                        if record["bytes_received"] > MAX_BYTES:
                            raise ValueError(f"document exceeded {MAX_BYTES} byte cap")
                        chunks.append(chunk)
                body = b"".join(chunks)
                validate_pdf(body, record["content_length"])
                digest = hashlib.sha256(body).hexdigest()
                filename = re.sub(r"[^A-Za-z0-9._-]", "_", pathlib.PurePosixPath(urlsplit(record["final_url"]).path).name)[:120]
                if not filename.lower().endswith(".pdf"):
                    filename = (filename or "document") + ".pdf"
                path = ARCHIVE / digest[:2] / f"{digest[:16]}_{filename}"
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    path.write_bytes(body)
                record.update({"ok": True, "validated": True, "sha256": digest,
                               "archive_path": path.as_posix(), "bytes_received": len(body),
                               "finished_at_utc": now_utc()})
                result["attempts"].append(record)
                result.update({"status": "ARCHIVED_VALIDATED_PDF", "bytes_received": len(body),
                               "sha256": digest, "archive_path": path.as_posix(),
                               "http_status": response.status_code})
                return result
        except Exception as exc:
            record.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:700],
                           "finished_at_utc": now_utc()})
            result["attempts"].append(record)
            if attempt < ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[attempt - 1])
    counts = [x["bytes_received"] for x in result["attempts"]]
    repeated = len(counts) == ATTEMPTS and counts[0] > 0 and len(set(counts)) == 1
    result.update({"status": "FAILED_REPEATED_SAME_BYTE_STALL" if repeated else "FAILED_VALIDATION_OR_TRANSPORT",
                   "bytes_received": counts[-1] if counts else 0})
    return result


def download_all(candidates: list[dict]) -> list[dict]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(download_one, candidates))


def transport_check(url: str, method: str) -> dict:
    started = time.monotonic()
    item = {"url": url, "method": method}
    try:
        if method == "requests":
            with requests.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, 30), stream=True) as response:
                count = 0
                for chunk in response.iter_content(16 * 1024):
                    if chunk:
                        count += len(chunk)
                        if count >= 128 * 1024:
                            break
                item.update({"http_status": response.status_code, "bytes_received": count,
                             "content_type": response.headers.get("Content-Type"), "ok": response.status_code == 200})
        else:
            with c_requests.Session(impersonate="chrome") as session:
                response = session.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, 30), stream=True)
                count = 0
                for chunk in response.iter_content(16 * 1024):
                    if chunk:
                        count += len(chunk)
                        if count >= 128 * 1024:
                            break
                item.update({"http_status": response.status_code, "bytes_received": count,
                             "content_type": response.headers.get("Content-Type"), "ok": response.status_code == 200})
    except Exception as exc:
        item.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]})
    item["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return item


def wayback_targets() -> list[str]:
    refresh = pathlib.Path("data/reports/weekly_market_document_refresh.json")
    urls = set(SNAPSHOT_HISTORY_TARGETS)
    if refresh.exists():
        data = json.loads(refresh.read_text(encoding="utf-8"))
        for row in data.get("records", []):
            url = row.get("source_url", "")
            host = (urlsplit(url).hostname or "").lower()
            if host in {"nseindia.com", "www.nseindia.com", "nsearchives.nseindia.com",
                        "archives.nseindia.com", "niftyindices.com", "www.niftyindices.com"}:
                urls.add(url)
    return sorted(urls)


def wayback_snapshot_url(timestamp: str, original: str) -> str:
    if not re.fullmatch(r"\\d{14}", timestamp) or original not in SNAPSHOT_CSV_TARGETS:
        raise ValueError("Wayback snapshot must reference a dated capture of an allowlisted Nifty 50 CSV")
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def validate_constituent_snapshot(payload: bytes) -> dict:
    text = payload.decode("utf-8-sig", errors="replace")
    if "<html" in text[:500].lower() or "<!doctype" in text[:500].lower():
        raise ValueError("Wayback response is HTML, not a constituent CSV")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("constituent CSV has no data rows")
    headers = {key.strip().lower(): key for key in (rows[0].keys() if rows else [])}
    symbol_key = next((headers[k] for k in ("symbol", "trading symbol", "ticker") if k in headers), None)
    isin_key = next((headers[k] for k in ("isin code", "isin") if k in headers), None)
    if not symbol_key or not isin_key:
        raise ValueError("constituent CSV must expose Symbol and ISIN columns")
    symbols = [row.get(symbol_key, "").strip().upper() for row in rows]
    isins = [row.get(isin_key, "").strip().replace(" ", "").upper() for row in rows]
    valid = [(s, i) for s, i in zip(symbols, isins) if s and re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", i)]
    return {
        "row_count": len(rows),
        "distinct_symbol_count": len(set(symbols) - {""}),
        "valid_isin_row_count": len(valid),
        "exactly_50_distinct_symbols": len(set(symbols) - {""}) == 50,
        "all_rows_have_valid_isin": len(valid) == len(rows),
        "symbols": sorted(set(symbols) - {""}),
    }


def archive_wayback_constituent_snapshots(session, target: str, cdx_rows: list[list[str]]) -> list[dict]:
    if target not in SNAPSHOT_CSV_TARGETS:
        return []
    WAYBACK_SNAPSHOT_ARCHIVE.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for row in cdx_rows[1:]:
        if len(row) < 6:
            continue
        timestamp, original, status, mimetype, cdx_digest, length = row[:6]
        if original != target or not timestamp.startswith(tuple(str(year) for year in range(2018, 2025))):
            continue
        if status != "200" or mimetype not in {"text/csv", "application/vnd.ms-excel", "text/plain"}:
            continue
        record = {"capture_timestamp": timestamp, "original_url": original, "cdx_digest": cdx_digest}
        try:
            response = session.get(
                wayback_snapshot_url(timestamp, original),
                headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*;q=0.5"},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            if response.status_code != 200:
                raise ValueError(f"Wayback snapshot returned HTTP {response.status_code}")
            payload = response.content
            if not payload or len(payload) > 5 * 1024 * 1024:
                raise ValueError("Wayback snapshot is empty or exceeds 5 MiB")
            validation = validate_constituent_snapshot(payload)
            digest = hashlib.sha256(payload).hexdigest()
            path = WAYBACK_SNAPSHOT_ARCHIVE / f"{timestamp}_{digest[:16]}.csv"
            if not path.exists():
                path.write_bytes(payload)
            record.update({
                "archive_path": path.as_posix(),
                "bytes_received": len(payload),
                "sha256": digest,
                "validation": validation,
                "status": (
                    "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"
                    if validation["exactly_50_distinct_symbols"] and validation["all_rows_have_valid_isin"]
                    else "ARCHIVED_SNAPSHOT_REQUIRES_REVIEW"
                ),
            })
        except Exception as exc:
            record.update({"status": "SNAPSHOT_FETCH_OR_VALIDATION_FAILED",
                           "error": f"{type(exc).__name__}: {exc}"[:700]})
        snapshots.append(record)
    return snapshots


def ingest_wayback() -> dict:
    WAYBACK_ARCHIVE.mkdir(parents=True, exist_ok=True)
    targets = wayback_targets()
    records, failures, snapshots = [], [], []
    with c_requests.Session(impersonate="chrome") as session:
        for target in targets:
            params = {"url": target, "output": "json", "filter": "statuscode:200",
                      "fl": "timestamp,original,statuscode,mimetype,digest,length",
                      "collapse": "digest"}
            if target in SNAPSHOT_HISTORY_TARGETS:
                params.update({"from": "2018", "to": "2024"})
            try:
                response = session.get(WAYBACK_CDX, params=params,
                                       headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                                       timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
                response.raise_for_status()
                payload = response.content
                digest = hashlib.sha256(payload).hexdigest()
                path = WAYBACK_ARCHIVE / f"{digest[:16]}.json"
                if not path.exists():
                    path.write_bytes(payload)
                rows = list(csv.reader(io.StringIO(response.text)))
                records.append({"target_url": target, "http_status": response.status_code,
                                "bytes_received": len(payload), "sha256": digest,
                                "archive_path": path.as_posix(), "retrieved_at_utc": now_utc(),
                                "row_count": max(0, len(rows) - 1),
                                "status": "CDX_METADATA_ARCHIVED"})
                snapshots.extend(archive_wayback_constituent_snapshots(session, target, rows))
            except Exception as exc:
                failures.append({"target_url": target, "retrieved_at_utc": now_utc(),
                                 "status": "CDX_QUERY_FAILED",
                                 "error": f"{type(exc).__name__}: {exc}"[:700]})
    report = {"schema_version": 2, "run_at_utc": now_utc(), "cdx_endpoint": WAYBACK_CDX,
              "targets_checked": len(targets), "records_archived": len(records),
              "failures": failures, "records": records, "constituent_snapshots": snapshots,
              "constituent_snapshot_count": len(snapshots),
              "limitations": ["CDX metadata and archived page captures are candidate evidence only.",
                              "Wayback capture dates are not membership effective dates.",
                              "A 50-row CSV is not accepted without primary-source and independent review.",
                              "No model, price, TRI, membership, or trading state is changed."]}
    WAYBACK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    WAYBACK_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    return report


def main() -> int:
    egress = get_egress_ip()
    candidates = source_candidates()
    transport_checks = [
        transport_check(WAYBACK_CDX + "?url=" + quote("https://www.nseindia.com/") + "&output=json", "requests"),
        transport_check(WAYBACK_CDX + "?url=" + quote("https://www.nseindia.com/") + "&output=json", "curl_cffi"),
        transport_check("https://nsearchives.nseindia.com/content/indices/ind_nifty50.pdf", "requests"),
        transport_check("https://nsearchives.nseindia.com/content/indices/ind_nifty50.pdf", "curl_cffi"),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        pdf_future = pool.submit(download_all, candidates)
        wayback_future = pool.submit(ingest_wayback)
        results = pdf_future.result()
        wayback = wayback_future.result()
    archived = sum(x["status"] == "ARCHIVED_VALIDATED_PDF" for x in results)
    failed = len(results) - archived
    report = {
        "schema_version": 1, "run_at_utc": now_utc(), "egress_ip": egress,
        "transport_checks": transport_checks, "candidate_count": len(candidates),
        "archived_count": archived, "failed_count": failed, "results": results,
        "status": "COMPLETE" if failed == 0 else "PARTIAL",
        "research_status": "RESEARCH_HOLD", "changes_to_model_data": False,
        "historical_prices_or_tri_modified": False, "holdout_accessed": False,
        "promotion_eligible": False, "paper_trading_eligible": False,
        "live_execution_enabled": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_count": len(candidates), "archived_count": archived,
        "failed_count": failed, "wayback_targets": wayback["targets_checked"],
        "wayback_archived": wayback["records_archived"],
        "wayback_failures": len(wayback["failures"]), "egress_ip": egress.get("ip"),
    }, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
