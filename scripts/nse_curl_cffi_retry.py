#!/usr/bin/env python3
"""Controlled curl_cffi retry for official NSE/Nifty Indices PDFs plus Wayback CDX ingestion.

Only complete, structurally bounded PDF bodies are archived and hashed. This is
source acquisition diagnostics only: it never updates model data or membership.
"""
from __future__ import annotations

import hashlib
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
    if not refresh.exists():
        return ["https://www.nseindia.com/resources/exchange-communication-circulars"]
    data = json.loads(refresh.read_text(encoding="utf-8"))
    urls = []
    for row in data.get("records", []):
        url = row.get("source_url", "")
        host = (urlsplit(url).hostname or "").lower()
        if host in {"nseindia.com", "www.nseindia.com", "nsearchives.nseindia.com",
                    "niftyindices.com", "www.niftyindices.com"}:
            urls.append(url)
    return sorted(set(urls))


def ingest_wayback() -> dict:
    WAYBACK_ARCHIVE.mkdir(parents=True, exist_ok=True)
    targets = wayback_targets()
    records, failures = [], []
    with c_requests.Session(impersonate="chrome") as session:
        for target in targets:
            params = {"url": target, "output": "json", "filter": "statuscode:200",
                      "fl": "timestamp,original,statuscode,mimetype,digest,length",
                      "collapse": "digest"}
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
                records.append({"target_url": target, "http_status": response.status_code,
                                "bytes_received": len(payload), "sha256": digest,
                                "archive_path": path.as_posix(), "retrieved_at_utc": now_utc(),
                                "row_count": max(0, len(response.text.splitlines()) - 1),
                                "status": "CDX_METADATA_ARCHIVED"})
            except Exception as exc:
                failures.append({"target_url": target, "retrieved_at_utc": now_utc(),
                                 "status": "CDX_QUERY_FAILED",
                                 "error": f"{type(exc).__name__}: {exc}"[:700]})
    report = {"schema_version": 1, "run_at_utc": now_utc(), "cdx_endpoint": WAYBACK_CDX,
              "targets_checked": len(targets), "records_archived": len(records),
              "failures": failures, "records": records,
              "limitations": ["CDX metadata only; archived payloads are not downloaded.",
                              "A CDX row does not establish source authenticity or document meaning.",
                              "No model, price, TRI, membership, or trading state is changed."]}
    WAYBACK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    WAYBACK_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
        pdf_future = pool.submit(lambda: [download_one(item) for item in candidates])
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
