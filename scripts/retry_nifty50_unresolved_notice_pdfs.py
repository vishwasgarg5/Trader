#!/usr/bin/env python3
"""Resumable retrieval of three unresolved official NSE Indices notice PDFs."""
from __future__ import annotations

import base64
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

REPO_URL = "https://github.com/vishwasgarg5/Trader"
USER_AGENT = f"Trader-NIFTY50-Notice-Evidence/1.0 (+{REPO_URL})"
STATE_PATH = pathlib.Path("data/reference/nifty50_unresolved_notice_state.json")
REPORT_PATH = pathlib.Path("data/reports/nifty50_unresolved_notice_retrieval.json")
ARCHIVE = pathlib.Path("data/reference/source_documents/nifty50_unresolved_notices")
CDX = "https://web.archive.org/cdx/search/cdx"
REQUEST_BUDGET = 12
RUNTIME_BUDGET = 15 * 60
MIN_INTERVAL = 3.0
TIMEOUT = (15, 45)
MAX_BYTES = 50 * 1024 * 1024

DOCUMENTS = {
    "NSE-ARCHIVE-2018-06-05-209df26d1951": "https://www.niftyindices.com/Press_Release/ind_prs05062018.pdf",
    "NSE-ARCHIVE-2019-07-16-3a8719394912": "https://www.niftyindices.com/Press_Release/ind_prs16072019_1.pdf",
    "NSE-ARCHIVE-2023-03-14-5b13b76a2af9": "https://www.niftyindices.com/Press_Release/ind_prs14032023.pdf",
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def stamp() -> str:
    return now().isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wayback_cdx_digest(data: bytes) -> str:
    """Return the unpadded Base32 SHA-1 digest used by Wayback CDX."""
    return base64.b32encode(hashlib.sha1(data).digest()).decode("ascii").rstrip("=")


def cdx_digest_matches(data: bytes, expected: str) -> bool:
    return bool(expected) and wayback_cdx_digest(data) == expected.strip().upper()


def atomic(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (dt - now()).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def direct_fallbacks(original: str) -> list[str]:
    path = urlsplit(original).path
    return list(dict.fromkeys([
        f"https://nsearchives.nseindia.com{path}",
        f"https://archives.nseindia.com{path}",
        f"https://www.niftyindices.com{path}",
        f"https://niftyindices.com{path}",
    ]))


def validate_pdf(data: bytes) -> None:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("PDF is empty or exceeds 50 MiB")
    if not data.startswith(b"%PDF"):
        raise ValueError("response does not start with PDF signature")
    if not data.rstrip().endswith(b"%%EOF"):
        raise ValueError("response does not contain a terminal PDF EOF marker")


class Budget:
    def __init__(self, state: dict):
        self.state = state
        self.started = time.monotonic()
        self.count = 0
        self.last = None
        saved_last = state.get("last_request_at_utc")
        if saved_last:
            try:
                self.last = datetime.fromisoformat(saved_last)
            except ValueError:
                self.last = None
        self.stop = None
        self.next_retry = None

    def request(self, session: requests.Session, url: str, params: dict | None, label: str):
        for attempt in range(1, 4):
            if self.count >= REQUEST_BUDGET:
                self.stop = "REQUEST_BUDGET_REACHED"
                return None
            if time.monotonic() - self.started >= RUNTIME_BUDGET:
                self.stop = "RUNTIME_BUDGET_REACHED"
                return None
            if self.last:
                delay = max(0, MIN_INTERVAL - (now() - self.last).total_seconds())
                if delay:
                    time.sleep(delay)
            self.count += 1
            self.last = now()
            self.state["last_request_at_utc"] = self.last.isoformat()
            try:
                response = session.get(url, params=params, headers={
                    "User-Agent": USER_AGENT, "Accept": "application/pdf,application/json,*/*;q=0.5",
                    "Accept-Encoding": "identity"
                }, timeout=TIMEOUT)
            except requests.RequestException as exc:
                self.state["attempt_log"].append({"at_utc": stamp(), "url": url, "label": label,
                                                  "attempt": attempt, "error": f"{type(exc).__name__}: {exc}"[:500]})
                if attempt == 3:
                    return None
                time.sleep(3 * attempt + random.uniform(0, 2))
                continue
            self.state["attempt_log"].append({"at_utc": stamp(), "url": url, "label": label,
                                              "attempt": attempt, "http_status": response.status_code})
            if response.status_code == 429:
                wait = retry_after(response.headers.get("Retry-After"))
                if wait is None:
                    wait = 30 * (2 ** (attempt - 1)) + random.uniform(0, 3)
                self.next_retry = (now() + timedelta(seconds=wait)).isoformat()
                self.state["next_retry_at_utc"] = self.next_retry
                self.stop = "HTTP_429_THROTTLED"
                return None
            if response.status_code in (500, 502, 503, 504) and attempt < 3:
                time.sleep(3 * attempt + random.uniform(0, 2))
                continue
            return response
        return None


def advance_direct_fallback(item: dict, budget: Budget, url: str) -> bool:
    """Move past a host only after transient retries are exhausted, never on a budget/429 stop."""
    if budget.stop is not None:
        return False
    item["next_direct_index"] += 1
    item.setdefault("fallback_errors", []).append({
        "url": url, "at_utc": stamp(), "reason": "request_failed_after_retries"
    })
    return True


def reconcile_exhausted_direct_fallback(item: dict, attempt_log: list[dict]) -> bool:
    """Migrate legacy state where three recorded timeouts did not advance the host index."""
    index = item.get("next_direct_index", 0)
    urls = item.get("direct_urls", [])
    if index >= len(urls):
        return False
    url = urls[index]
    matching = [entry for entry in attempt_log if entry.get("url") == url]
    recent = matching[-3:]
    if len(recent) != 3:
        return False
    if [entry.get("attempt") for entry in recent] != [1, 2, 3]:
        return False
    if any("error" not in entry or "http_status" in entry for entry in recent):
        return False
    item["next_direct_index"] = index + 1
    item.setdefault("fallback_errors", []).append({
        "url": url, "at_utc": stamp(),
        "reason": "migrated_legacy_three_transient_failures"
    })
    return True


def load_state() -> dict:
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    else:
        state = {"schema_version": 1, "documents": {}, "attempt_log": [],
                 "created_at_utc": stamp(), "last_request_at_utc": None}
    for doc_id, original in DOCUMENTS.items():
        state["documents"].setdefault(doc_id, {
            "original_url": original, "direct_urls": direct_fallbacks(original),
            "next_direct_index": 0, "cdx_checked": False, "cdx_captures": [],
            "next_capture_index": 0, "status": "PENDING",
            "attempts": [], "classification": "UNCLASSIFIED_PENDING_PRIMARY_DOCUMENT_REVIEW"
        })
        item = state["documents"][doc_id]
        if reconcile_exhausted_direct_fallback(item, state.get("attempt_log", [])):
            atomic(STATE_PATH, state)
    return state


def parse_cdx_json(payload: bytes | str) -> list[list[str]]:
    """Parse CDX output=json, treating a valid empty result as zero captures."""
    if isinstance(payload, bytes):
        text = payload.decode("utf-8-sig", errors="strict")
    else:
        text = payload.lstrip("\\ufeff")
    try:
        rows = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        preview = text[:240].replace("\\n", " ")
        raise ValueError(f"CDX response is not valid JSON: {type(exc).__name__}; body={preview!r}") from exc
    if rows == []:
        return []
    if not isinstance(rows, list) or any(not isinstance(row, list) for row in rows):
        preview = text[:240].replace("\\n", " ")
        raise ValueError(f"CDX JSON must be an array of rows; body={preview!r}")
    return rows


def extract_pdf(data: bytes) -> dict:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data), strict=False)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        content = (page.extract_text() or "").strip()
        if content:
            pages.append({"page": i, "text": content[:12000]})
    return {"page_count": len(reader.pages), "text_extraction": "AVAILABLE" if pages else "NO_EXTRACTABLE_TEXT",
            "pages": pages}


def save_pdf(doc_id: str, data: bytes, source_url: str, evidence_class: str) -> dict:
    validate_pdf(data)
    file_hash = digest(data)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    path = ARCHIVE / f"{doc_id}_{file_hash[:16]}.pdf"
    if not path.exists():
        path.write_bytes(data)
    try:
        extracted = extract_pdf(data)
    except Exception as exc:
        extracted = {"text_extraction": "FAILED", "error": f"{type(exc).__name__}: {exc}"[:500]}
    return {"status": "RETRIEVED_PENDING_PRIMARY_SCOPE_REVIEW", "archive_path": path.as_posix(),
            "sha256": file_hash, "bytes_received": len(data), "source_url": source_url,
            "evidence_class": evidence_class, "retrieved_at_utc": stamp(),
            "pdf_validation": "SIGNATURE_AND_EOF_VALID", "extracted_content": extracted}


def run() -> dict:
    state = load_state()
    saved_retry = state.get("next_retry_at_utc")
    if saved_retry:
        try:
            if datetime.fromisoformat(saved_retry) > now():
                report = {"schema_version": 1, "run_at_utc": stamp(), "status": "PARTIAL",
                          "stop_reason": "WAITING_FOR_RETRY_AFTER", "next_retry_at_utc": saved_retry,
                          "documents": state["documents"], "attempt_log": state["attempt_log"]}
                atomic(REPORT_PATH, report)
                return report
        except ValueError:
            pass
    state.pop("next_retry_at_utc", None)
    budget = Budget(state)
    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        for doc_id, item in state["documents"].items():
            if item["status"] == "RETRIEVED_PENDING_PRIMARY_SCOPE_REVIEW":
                continue
            while item["next_direct_index"] < len(item["direct_urls"]):
                url = item["direct_urls"][item["next_direct_index"]]
                response = budget.request(session, url, None, f"direct:{doc_id}")
                if response is None:
                    # Exhausted transient retries on this host: persist progress to the
                    # next official-host fallback. Do not advance on a budget/429 stop.
                    if advance_direct_fallback(item, budget, url):
                        atomic(STATE_PATH, state)
                    break
                item["attempts"].append({"url": url, "at_utc": stamp(), "http_status": response.status_code})
                item["next_direct_index"] += 1
                if response.status_code == 200:
                    try:
                        saved = save_pdf(doc_id, response.content, url, "OFFICIAL_HOST_BYTES")
                        item.update(saved)
                        atomic(STATE_PATH, state)
                        break
                    except Exception as exc:
                        item["attempts"][-1]["validation_error"] = f"{type(exc).__name__}: {exc}"[:500]
                atomic(STATE_PATH, state)
                if not budget.count < REQUEST_BUDGET or budget.stop:
                    break
            if item["status"] == "RETRIEVED_PENDING_PRIMARY_SCOPE_REVIEW" or budget.stop:
                if budget.stop:
                    break
                continue
            if item["next_direct_index"] >= len(item["direct_urls"]) and not item["cdx_checked"]:
                response = budget.request(session, CDX, {
                    "url": item["original_url"], "output": "json",
                    "filter": "statuscode:200", "collapse": "digest",
                    "fl": "timestamp,original,statuscode,mimetype,digest,length",
                    "from": "2018", "to": "2024"
                }, f"cdx:{doc_id}")
                if response is None:
                    break
                if response.status_code == 200:
                    try:
                        rows = parse_cdx_json(response.content)
                        # A syntactically valid empty CDX result is a completed lookup,
                        # not a parser failure. Preserve the distinction in state/report.
                        item["cdx_response_row_count"] = len(rows)
                        item["cdx_captures"] = rows[1:] if rows else []
                        item["cdx_result"] = "EMPTY" if not rows else "ROWS_RETURNED"
                        item["cdx_content_type"] = response.headers.get("Content-Type", "")[:160]
                        item["cdx_metadata_sha256"] = digest(response.content)
                        item.pop("cdx_error", None)
                        item["cdx_checked"] = True
                    except Exception as exc:
                        item["cdx_error"] = f"{type(exc).__name__}: {exc}"[:500]
                else:
                    item["cdx_error"] = f"CDX returned HTTP {response.status_code}"
                atomic(STATE_PATH, state)
            while item["cdx_checked"] and item["next_capture_index"] < len(item["cdx_captures"]):
                row = item["cdx_captures"][item["next_capture_index"]]
                if len(row) < 6:
                    item["next_capture_index"] += 1
                    continue
                ts, original, status, mimetype, cdx_digest, length = row[:6]
                if status != "200" or not re.fullmatch(r"\d{14}", ts):
                    item["next_capture_index"] += 1
                    continue
                archive_url = f"https://web.archive.org/web/{ts}id_/{original}"
                response = budget.request(session, archive_url, None, f"wayback:{doc_id}:{ts}")
                if response is None:
                    break
                item["attempts"].append({"url": archive_url, "at_utc": stamp(),
                                         "http_status": response.status_code, "cdx_digest": cdx_digest})
                item["next_capture_index"] += 1
                if response.status_code == 200:
                    actual_cdx_digest = wayback_cdx_digest(response.content)
                    digest_match = cdx_digest_matches(response.content, cdx_digest)
                    item["attempts"][-1]["cdx_digest_actual"] = actual_cdx_digest
                    item["attempts"][-1]["cdx_digest_validation"] = "MATCH" if digest_match else "MISMATCH"
                    if not digest_match:
                        item["attempts"][-1]["validation_error"] = "Wayback replay body does not match the CDX SHA-1 digest"
                        atomic(STATE_PATH, state)
                        continue
                    try:
                        saved = save_pdf(doc_id, response.content, archive_url, "WAYBACK_SUPPLEMENTARY_BYTES")
                        item.update(saved)
                        item["cdx_digest"] = cdx_digest
                        item["cdx_digest_validation"] = "MATCH"
                        break
                    except Exception as exc:
                        item["attempts"][-1]["validation_error"] = f"{type(exc).__name__}: {exc}"[:500]
                atomic(STATE_PATH, state)
                if budget.stop:
                    break
            if item["status"] == "PENDING" and item["cdx_checked"] and item["next_capture_index"] >= len(item["cdx_captures"]):
                item["status"] = "DOCUMENT_UNAVAILABLE"
                item["unavailable_reason"] = "All direct official-host URLs and returned Wayback captures were attempted without a valid PDF."
                item["classification"] = "UNCLASSIFIED_SCOPE_REVIEW_REQUIRED"
            atomic(STATE_PATH, state)
            if budget.stop:
                break

    complete = all(x["status"] != "PENDING" for x in state["documents"].values())
    report = {"schema_version": 1, "run_at_utc": stamp(),
              "status": "COMPLETE" if complete else "PARTIAL",
              "stop_reason": budget.stop or ("ALL_DOCUMENTS_ATTEMPTED" if complete else "WORK_REMAINS"),
              "next_retry_at_utc": budget.next_retry,
              "requests_this_run": budget.count, "request_budget": REQUEST_BUDGET,
              "runtime_seconds": round(time.monotonic() - budget.started, 2),
              "documents": state["documents"], "attempt_log": state["attempt_log"],
              "scope_rule": "No document is classified out of NIFTY 50 scope by filename, archive title, or prior assessment. Primary PDF content must be reviewed for exact index, page, section, and text.",
              "limitations": ["A retrieved PDF is not a membership decision.",
                              "A document unavailable after all recorded attempts remains unresolved, not out of scope.",
                              "No canonical membership, model, holdout, or trading state is modified."]}
    atomic(STATE_PATH, state)
    atomic(REPORT_PATH, report)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
