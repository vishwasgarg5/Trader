#!/usr/bin/env python3
"""Resumable, rate-limited Wayback acquisition for historical NIFTY 50 CSV snapshots.

All captures are supplementary evidence. This tool never changes the canonical
membership ledger, model inputs, holdout, or trading permissions.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import pathlib
import random
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

ROOT = pathlib.Path(".")
STATE_PATH = ROOT / "data/reference/wayback_nifty50_acquisition_state.json"
REPORT_PATH = ROOT / "data/reports/wayback_nifty50_quarterly_coverage.json"
MANIFEST_DIR = ROOT / "data/reference/wayback_nifty50_cdx"
SNAPSHOT_DIR = ROOT / "data/reference/source_documents/wayback_nifty50_snapshots"
CDX_URL = "https://web.archive.org/cdx/search/cdx"
REPO_URL = "https://github.com/vishwasgarg5/Trader"
USER_AGENT = f"Trader-NIFTY50-Historical-Evidence/1.0 (+{REPO_URL})"
TARGETS = [
    "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "https://niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "https://www1.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://www.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
]
YEARS = range(2018, 2025)
REQUEST_BUDGET = 24
RUNTIME_BUDGET_SECONDS = 20 * 60
MIN_REQUEST_INTERVAL_SECONDS = 3.0
MAX_RETRIES = 3
CONNECT_TIMEOUT = 15
READ_TIMEOUT = 45
MAX_CSV_BYTES = 5 * 1024 * 1024
ALLOWED_MIME = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain", "application/octet-stream"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utcnow().isoformat()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def wayback_cdx_digest(payload: bytes) -> str:
    """Internet Archive CDX body digest: SHA-1 encoded as unpadded Base32."""
    return base64.b32encode(hashlib.sha1(payload).digest()).decode("ascii").rstrip("=")


def cdx_digest_matches(payload: bytes, expected: str) -> bool:
    return wayback_cdx_digest(payload) == expected


def atomic_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_state() -> dict:
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    else:
        state = {"schema_version": 1, "created_at_utc": iso_now(), "targets": {},
                 "pending_snapshots": [], "completed_snapshots": [],
                 "attempt_log": [], "last_request_at_utc": None}
    for target in TARGETS:
        state["targets"].setdefault(target, {"metadata_done": False, "collapsed_done": False,
                                              "full_capture_count": 0, "candidate_count": 0})
    # Reconcile existing downloads against CDX body digests before counting them usable.
    for item in state.get("completed_snapshots", []):
        archive_path = pathlib.Path(item.get("archive_path", ""))
        expected = item.get("cdx_digest")
        if expected and archive_path.is_file():
            actual = wayback_cdx_digest(archive_path.read_bytes())
            item["computed_cdx_digest"] = actual
            if actual != expected:
                item.setdefault("pre_digest_validation_status", item.get("status"))
                item["status"] = "CDX_DIGEST_MISMATCH"
                item["cdx_digest_validation"] = "MISMATCH"
            else:
                item["cdx_digest_validation"] = "MATCH"
    return state


def quarter_key(timestamp: str) -> str:
    dt = datetime.strptime(timestamp[:8], "%Y%m%d")
    return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"


def all_quarters() -> list[str]:
    return [f"{year}-Q{q}" for year in YEARS for q in range(1, 5)]


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value.strip()))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (dt - utcnow()).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


class RunBudget:
    def __init__(self, state: dict):
        self.state = state
        self.started = time.monotonic()
        self.requests = 0
        self.last_request = None
        saved = state.get("last_request_at_utc")
        if saved:
            try:
                self.last_request = datetime.fromisoformat(saved)
            except ValueError:
                self.last_request = None
        self.throttled = False
        self.stop_reason = None
        self.next_retry_at = None

    def can_request(self) -> bool:
        if self.requests >= REQUEST_BUDGET:
            self.stop_reason = "REQUEST_BUDGET_REACHED"
            return False
        if time.monotonic() - self.started >= RUNTIME_BUDGET_SECONDS:
            self.stop_reason = "RUNTIME_BUDGET_REACHED"
            return False
        return True

    def before_request(self) -> bool:
        if not self.can_request():
            return False
        if self.last_request is not None:
            elapsed = (utcnow() - self.last_request).total_seconds()
            wait = max(0.0, MIN_REQUEST_INTERVAL_SECONDS - elapsed)
            if wait:
                if time.monotonic() - self.started + wait >= RUNTIME_BUDGET_SECONDS:
                    self.stop_reason = "RUNTIME_BUDGET_REACHED_DURING_PACING"
                    return False
                time.sleep(wait)
        return self.can_request()

    def record_request(self, state: dict) -> None:
        self.requests += 1
        self.last_request = utcnow()
        state["last_request_at_utc"] = self.last_request.isoformat()


def request_one(session: requests.Session, url: str, params: dict | None,
                state: dict, budget: RunBudget, label: str) -> requests.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        if not budget.before_request():
            return None
        budget.record_request(state)
        try:
            response = session.get(url, params=params, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/csv,*/*;q=0.5",
                "Accept-Encoding": "identity",
            }, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
            state["attempt_log"].append({"at_utc": iso_now(), "label": label,
                                         "attempt": attempt, "http_status": response.status_code})
            if response.status_code == 429:
                delay = parse_retry_after(response.headers.get("Retry-After"))
                if delay is None:
                    delay = min(300, 30 * (2 ** (attempt - 1))) + random.uniform(0, 3)
                budget.throttled = True
                budget.stop_reason = "HTTP_429_THROTTLED"
                budget.next_retry_at = (utcnow() + timedelta(seconds=delay)).isoformat()
                state["next_retry_at_utc"] = budget.next_retry_at
                return None
            if response.status_code in (500, 502, 503, 504) and attempt < MAX_RETRIES:
                delay = min(30, 3 * (2 ** (attempt - 1))) + random.uniform(0, 2)
                time.sleep(delay)
                continue
            return response
        except requests.RequestException as exc:
            state["attempt_log"].append({"at_utc": iso_now(), "label": label,
                                         "attempt": attempt, "error": f"{type(exc).__name__}: {exc}"[:500]})
            if attempt == MAX_RETRIES:
                return None
            time.sleep(min(30, 3 * (2 ** (attempt - 1))) + random.uniform(0, 2))
    return None


def cdx_params(target: str, collapsed: bool) -> dict:
    params = {"url": target, "output": "json",
              "filter": "statuscode:200",
              "fl": "timestamp,original,statuscode,mimetype,digest,length",
              "from": "2018", "to": "2024"}
    if collapsed:
        params["collapse"] = "digest"
    return params


def parse_cdx(payload: str) -> list[list[str]]:
    rows = json.loads(payload)
    if not isinstance(rows, list) or not rows or not all(isinstance(row, list) for row in rows):
        raise ValueError("CDX response is not a JSON array of rows")
    if rows[0][:3] != ["timestamp", "original", "statuscode"]:
        raise ValueError("CDX response header is not the expected six-field schema")
    return rows[1:]


def archive_cdx_payload(target: str, kind: str, payload: bytes) -> dict:
    digest = sha256(payload)
    path = MANIFEST_DIR / f"{kind}_{digest[:20]}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)
    return {"target_url": target, "kind": kind, "archive_path": path.as_posix(),
            "sha256": digest, "bytes_received": len(payload), "retrieved_at_utc": iso_now()}


def header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").strip().lower())


def validate_snapshot(payload: bytes) -> dict:
    if not payload or len(payload) > MAX_CSV_BYTES:
        raise ValueError("CSV is empty or exceeds 5 MiB")
    text = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("CSV encoding is not supported")
    if "<html" in text[:500].lower() or "<!doctype" in text[:500].lower():
        raise ValueError("response is HTML, not a CSV")
    reader = csv.DictReader(io.StringIO(text))
    original_headers = reader.fieldnames or []
    if not original_headers:
        raise ValueError("CSV has no header")
    aliases = {
        "symbol": {"symbol", "tradingsymbol", "ticker", "tradingsymbols"},
        "isin": {"isincode", "isin", "isinno", "isinnumber"},
        "company": {"companyname", "name", "securityname"},
    }
    normalized = {header_key(h): h for h in original_headers if h}
    mapping = {}
    for field, names in aliases.items():
        found = next((normalized[n] for n in names if n in normalized), None)
        if found:
            mapping[field] = found
    symbol_column = mapping.get("symbol")
    if not symbol_column:
        raise ValueError(f"no recognized symbol column; headers={original_headers!r}")
    rows = list(reader)
    symbols = [str(row.get(symbol_column) or "").strip().upper() for row in rows]
    symbols = [s for s in symbols if s]
    distinct = sorted(set(symbols))
    if len(distinct) < 40 or len(distinct) > 55:
        raise ValueError(f"implausible constituent count: {len(distinct)} distinct symbols")
    isin_column = mapping.get("isin")
    isins = [str(row.get(isin_column) or "").strip().upper().replace(" ", "")
             for row in rows] if isin_column else []
    valid_isins = [v for v in isins if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", v)]
    return {
        "row_count": len(rows), "distinct_symbol_count": len(distinct),
        "symbols": distinct, "original_headers": original_headers,
        "normalized_header_mapping": mapping,
        "isin_status": ("HAS_ISIN" if isin_column and len(valid_isins) == len(rows)
                        else "PARTIAL_ISIN" if valid_isins else "NO_ISIN"),
        "valid_isin_row_count": len(valid_isins),
        "duplicate_symbol_rows": len(symbols) - len(distinct),
        "exactly_50_distinct_symbols": len(distinct) == 50,
        "candidate_status": ("50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"
                             if len(distinct) == 50 else "NON_50_SNAPSHOT_REQUIRES_REVIEW"),
    }


def capture_key(item: dict) -> str:
    return f"{item['original_url']}|{item['capture_timestamp']}|{item.get('cdx_digest','')}"


def capture_matches_target(original: str, target: str) -> bool:
    """Allow scheme/standard-port variants of the queried URL, but not other hosts or paths."""
    try:
        captured = urlsplit(original)
        requested = urlsplit(target)
        requested_hosts = {requested.hostname}
        # NSE's apex and www hostnames serve the same official constituent path.
        if requested.hostname == "www.nseindia.com":
            requested_hosts.add("nseindia.com")
        return (
            captured.scheme in {"http", "https"}
            and requested.scheme in {"http", "https"}
            and captured.hostname in requested_hosts
            and captured.path == requested.path
            and captured.query == ""
            and captured.fragment == ""
            and captured.port in (None, 80, 443)
        )
    except ValueError:
        return False


def add_collapsed_captures(state: dict, target: str, rows: list[list[str]]) -> int:
    known = {capture_key(x) for x in state["pending_snapshots"] + state["completed_snapshots"]}
    added = 0
    for row in rows:
        if len(row) < 6:
            continue
        timestamp, original, status, mimetype, digest, length = row[:6]
        if not capture_matches_target(original, target) or status != "200" or mimetype.lower() not in ALLOWED_MIME:
            continue
        if len(timestamp) != 14 or not timestamp[:4].isdigit() or int(timestamp[:4]) not in YEARS:
            continue
        item = {"capture_timestamp": timestamp, "original_url": original,
                "http_status": 200, "mimetype": mimetype, "cdx_digest": digest,
                "cdx_length": length, "quarter": quarter_key(timestamp),
                "status": "PENDING_DOWNLOAD"}
        key = capture_key(item)
        if key not in known:
            state["pending_snapshots"].append(item)
            known.add(key)
            added += 1
    state["pending_snapshots"].sort(key=lambda x: (x["capture_timestamp"], x["original_url"]))
    return added


def add_full_metadata_quarter_candidates(state: dict, records: list[dict]) -> int:
    """Recover one verified-download candidate for quarters hidden by digest collapse."""
    pending = state.setdefault("pending_snapshots", [])
    completed = state.setdefault("completed_snapshots", [])
    verified_quarters = {
        item.get("quarter") for item in completed
        if item.get("cdx_digest_validation") == "MATCH"
        and item.get("status") == "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"
    }
    pending_quarters = {item.get("quarter") for item in pending}
    known = {capture_key(item) for item in pending + completed}
    added = 0
    for record in records:
        for capture in record.get("captures", []):
            quarter = capture.get("quarter")
            timestamp = capture.get("timestamp", "")
            original = capture.get("original_url", "")
            cdx_digest = capture.get("digest", "")
            if quarter in verified_quarters or quarter in pending_quarters:
                continue
            if capture.get("statuscode") != "200" or capture.get("mimetype", "").lower() not in ALLOWED_MIME:
                continue
            if not re.fullmatch("[0-9]{14}", timestamp):
                continue
            if not any(capture_matches_target(original, target) for target in TARGETS):
                continue
            item = {
                "capture_timestamp": timestamp, "original_url": original,
                "http_status": 200, "mimetype": capture.get("mimetype", ""),
                "cdx_digest": cdx_digest, "cdx_length": capture.get("length", ""),
                "quarter": quarter, "status": "PENDING_DOWNLOAD",
                "candidate_source": "FULL_CDX_QUARTER_GAP_RECOVERY"
            }
            key = capture_key(item)
            if key in known:
                continue
            pending.append(item)
            known.add(key)
            pending_quarters.add(quarter)
            added += 1
    pending.sort(key=lambda x: (x["capture_timestamp"], x["original_url"]))
    return added


def snapshot_url(timestamp: str, original: str) -> str:
    if not any(capture_matches_target(original, target) for target in TARGETS) or not re.fullmatch(r"\d{14}", timestamp):
        raise ValueError("snapshot URL requires an allowlisted host/path and 14-digit timestamp")
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def download_capture(session: requests.Session, item: dict, state: dict,
                     budget: RunBudget) -> dict | None:
    response = request_one(session, snapshot_url(item["capture_timestamp"], item["original_url"]),
                           None, state, budget, f"snapshot:{item['capture_timestamp']}")
    if response is None:
        return None
    if response.status_code != 200:
        item.update({"status": "FETCH_FAILED", "last_http_status": response.status_code,
                     "last_attempt_at_utc": iso_now(), "response_url": response.url})
        return item
    actual_cdx_digest = wayback_cdx_digest(response.content)
    if item.get("cdx_digest") and actual_cdx_digest != item["cdx_digest"]:
        item.update({
            "status": "CDX_DIGEST_MISMATCH",
            "expected_cdx_digest": item["cdx_digest"],
            "computed_cdx_digest": actual_cdx_digest,
            "response_url": response.url,
            "memento_datetime": response.headers.get("Memento-Datetime"),
            "content_encoding": response.headers.get("Content-Encoding"),
            "last_attempt_at_utc": iso_now(),
        })
        return item
    try:
        validation = validate_snapshot(response.content)
        digest = sha256(response.content)
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SNAPSHOT_DIR / f"{item['capture_timestamp']}_{digest[:16]}.csv"
        if not path.exists():
            path.write_bytes(response.content)
        item.update({"status": validation["candidate_status"], "archive_path": path.as_posix(),
                     "bytes_received": len(response.content), "sha256": digest,
                     "validation": validation, "retrieved_at_utc": iso_now(),
                     "evidence_class": "WAYBACK_SUPPLEMENTARY",
                     "computed_cdx_digest": actual_cdx_digest, "cdx_digest_validation": "MATCH",
                     "response_url": response.url,
                     "memento_datetime": response.headers.get("Memento-Datetime"),
                     "content_encoding": response.headers.get("Content-Encoding")})
    except Exception as exc:
        item.update({"status": "SNAPSHOT_INVALID", "error": f"{type(exc).__name__}: {exc}"[:700],
                     "retrieved_at_utc": iso_now()})
    return item


def build_coverage(state: dict, cdx_metadata: list[dict]) -> dict:
    all_rows = []
    for rec in cdx_metadata:
        all_rows.extend(rec.get("captures", []))
    usable = [x for x in state["completed_snapshots"]
              if x.get("status") in {"50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW",
                                     "NON_50_SNAPSHOT_REQUIRES_REVIEW"}]
    quarters = {}
    for q in all_quarters():
        metadata = [x for x in all_rows if x.get("quarter") == q]
        retrieved = [x for x in state["completed_snapshots"] if x.get("quarter") == q]
        good = [x for x in usable if x.get("quarter") == q]
        quarters[q] = {
            "status": ("USABLE" if good else "AVAILABLE" if metadata else
                       "NOT_YET_ATTEMPTED" if not all(state["targets"][t]["metadata_done"] for t in TARGETS)
                       else "MISSING"),
            "full_cdx_capture_count": len(metadata),
            "downloaded_capture_count": len(retrieved),
            "usable_capture_count": len(good),
            "captures": [{"timestamp": x.get("capture_timestamp"),
                          "original_url": x.get("original_url"),
                          "status": x.get("status"), "sha256": x.get("sha256")}
                         for x in retrieved],
        }
    return quarters


def run() -> dict:
    state = load_state()
    saved_retry = state.get("next_retry_at_utc")
    if saved_retry:
        try:
            retry_at = datetime.fromisoformat(saved_retry)
            if retry_at > utcnow():
                report = {
                    "schema_version": 1, "run_at_utc": iso_now(), "status": "PARTIAL",
                    "stop_reason": "WAITING_FOR_RETRY_AFTER", "next_retry_at_utc": saved_retry,
                    "requests_this_run": 0, "request_budget": REQUEST_BUDGET,
                    "runtime_seconds": 0, "runtime_budget_seconds": RUNTIME_BUDGET_SECONDS,
                    "targets_complete": sum(1 for t in TARGETS if state["targets"][t]["metadata_done"] and state["targets"][t]["collapsed_done"]),
                    "targets_total": len(TARGETS), "pending_snapshot_downloads": len(state["pending_snapshots"]),
                    "completed_snapshot_downloads": len(state["completed_snapshots"]),
                    "usable_quarters": sum(1 for v in build_coverage(state, state.get("full_cdx_metadata", [])).values() if v["status"] == "USABLE"),
                    "quarter_count": 28,
                    "quarterly_coverage": build_coverage(state, state.get("full_cdx_metadata", [])),
                    "full_cdx_metadata_records": state.get("full_cdx_metadata", []),
                    "collapsed_download_candidate_records": state.get("collapsed_cdx_metadata", []),
                    "target_errors": state.get("target_errors", []),
                    "limitations": ["Wayback Retry-After is still in force; no request was sent.",
                                    "Wayback captures are supplementary and never effective-date decisions."]
                }
                atomic_json(REPORT_PATH, report)
                return report
        except ValueError:
            pass
    state.pop("next_retry_at_utc", None)
    budget = RunBudget(state)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    metadata_records = state.setdefault("full_cdx_metadata", [])
    collapsed_records = state.setdefault("collapsed_cdx_metadata", [])
    state.setdefault("target_errors", [])

    # Re-read saved collapsed manifests so a later code fix can recover candidates
    # that an earlier exact-URL filter skipped. capture_key keeps this idempotent.
    for record in collapsed_records:
        target = record.get("target_url")
        archive_path = pathlib.Path(record.get("archive_path", ""))
        if target not in TARGETS or not archive_path.is_file():
            continue
        try:
            rows = parse_cdx(archive_path.read_text(encoding="utf-8"))
            add_collapsed_captures(state, target, rows)
        except Exception as exc:
            state["target_errors"].append({
                "target_url": target, "kind": "COLLAPSED_CDX_REPLAY",
                "at_utc": iso_now(), "error": str(exc)[:500]
            })

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        for target in TARGETS:
            if not budget.can_request() or budget.throttled:
                break
            target_state = state["targets"][target]
            if not target_state["metadata_done"]:
                response = request_one(session, CDX_URL, cdx_params(target, False), state, budget,
                                       f"cdx-full:{target}")
                if response is None:
                    break
                if response.status_code == 200:
                    try:
                        rows = parse_cdx(response.text)
                        captures = [{"timestamp": r[0], "original_url": r[1],
                                     "statuscode": r[2], "mimetype": r[3], "digest": r[4],
                                     "length": r[5], "quarter": quarter_key(r[0])}
                                    for r in rows if len(r) >= 6 and len(r[0]) == 14
                                    and r[0][:4].isdigit() and int(r[0][:4]) in YEARS]
                        archived = archive_cdx_payload(target, "full", response.content)
                        archived["capture_count"] = len(captures)
                        archived["captures"] = captures
                        metadata_records.append(archived)
                        target_state.update({"metadata_done": True, "full_capture_count": len(captures)})
                    except Exception as exc:
                        state["target_errors"].append({"target_url": target, "kind": "FULL_CDX",
                                                       "at_utc": iso_now(), "error": str(exc)[:500]})
                else:
                    state["target_errors"].append({"target_url": target, "kind": "FULL_CDX",
                                                   "at_utc": iso_now(), "http_status": response.status_code})
                atomic_json(STATE_PATH, state)
            if budget.throttled or not budget.can_request():
                break
            if not target_state["collapsed_done"]:
                response = request_one(session, CDX_URL, cdx_params(target, True), state, budget,
                                       f"cdx-collapsed:{target}")
                if response is None:
                    break
                if response.status_code == 200:
                    try:
                        rows = parse_cdx(response.text)
                        archived = archive_cdx_payload(target, "collapsed", response.content)
                        archived["capture_count"] = len(rows)
                        collapsed_records.append(archived)
                        target_state["candidate_count"] = add_collapsed_captures(state, target, rows)
                        target_state["collapsed_done"] = True
                    except Exception as exc:
                        state["target_errors"].append({"target_url": target, "kind": "COLLAPSED_CDX",
                                                       "at_utc": iso_now(), "error": str(exc)[:500]})
                else:
                    state["target_errors"].append({"target_url": target, "kind": "COLLAPSED_CDX",
                                                   "at_utc": iso_now(), "http_status": response.status_code})
                atomic_json(STATE_PATH, state)
        add_full_metadata_quarter_candidates(state, metadata_records)
        atomic_json(STATE_PATH, state)

        while state["pending_snapshots"] and budget.can_request() and not budget.throttled:
            item = state["pending_snapshots"][0]
            result = download_capture(session, item, state, budget)
            if result is None:
                break
            state["pending_snapshots"].pop(0)
            state["completed_snapshots"].append(result)
            atomic_json(STATE_PATH, state)

    all_metadata = []
    for rec in metadata_records:
        all_metadata.extend(rec.get("captures", []))
    quarters = build_coverage(state, metadata_records)
    complete_targets = all(state["targets"][t]["metadata_done"] and state["targets"][t]["collapsed_done"]
                           for t in TARGETS)
    pending = len(state["pending_snapshots"])
    status = "COMPLETE" if complete_targets and pending == 0 else "PARTIAL"
    report = {
        "schema_version": 1, "run_at_utc": iso_now(), "status": status,
        "stop_reason": budget.stop_reason or ("HTTP_429_THROTTLED" if budget.throttled else "WORK_REMAINING"),
        "next_retry_at_utc": budget.next_retry_at,
        "requests_this_run": budget.requests, "request_budget": REQUEST_BUDGET,
        "runtime_seconds": round(time.monotonic() - budget.started, 2),
        "runtime_budget_seconds": RUNTIME_BUDGET_SECONDS,
        "targets_complete": sum(1 for t in TARGETS if state["targets"][t]["metadata_done"] and state["targets"][t]["collapsed_done"]),
        "targets_total": len(TARGETS), "pending_snapshot_downloads": pending,
        "completed_snapshot_downloads": len(state["completed_snapshots"]),
        "usable_quarters": sum(1 for v in quarters.values() if v["status"] == "USABLE"),
        "quarter_count": len(quarters), "quarterly_coverage": quarters,
        "full_cdx_metadata_records": metadata_records,
        "collapsed_download_candidate_records": collapsed_records,
        "target_errors": state["target_errors"],
        "limitations": [
            "All Wayback captures are supplementary evidence, never effective-date decisions.",
            "CDX digest collapse reduces download candidates; uncollapsed metadata is retained for capture windows.",
            "50-row snapshots are candidate anchors only; non-50 snapshots are retained for review.",
            "Missing archive quarters are reported and are not treated as proof of non-membership.",
            "No canonical membership, model, price/TRI, holdout, or trading state is modified."
        ],
    }
    atomic_json(STATE_PATH, state)
    atomic_json(REPORT_PATH, report)
    print(json.dumps({k: report[k] for k in ("status", "stop_reason", "requests_this_run",
          "completed_snapshot_downloads", "pending_snapshot_downloads", "usable_quarters")}, indent=2))
    return report


if __name__ == "__main__":
    run()
