"""Shared, fail-closed HTTP acquisition for official market-source evidence.

The fetcher is transport infrastructure only. It does not interpret documents or
promote source content into research data.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import pathlib
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from curl_cffi import CurlHttpVersion, CurlOpt, requests as curl_requests

DEFAULT_TIMEOUT = (20, 180)
DEFAULT_ATTEMPTS = 3
BACKOFF_SECONDS = (2, 5)
CHUNK_SIZE = 64 * 1024
IP_ECHO_URL = "https://api.ipify.org?format=json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_official_url(url: str, allowed_hosts: set[str]) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in allowed_hosts:
        raise ValueError("URL must use HTTPS and an explicitly allowlisted official host")
    if parsed.username or parsed.password:
        raise ValueError("credentials in source URLs are not permitted")


def egress_identity() -> dict:
    record = {"checked_at_utc": utc_now(), "service": IP_ECHO_URL}
    try:
        with curl_requests.Session(impersonate="chrome") as session:
            response = session.get(IP_ECHO_URL, timeout=(10, 15))
            response.raise_for_status()
            value = response.json().get("ip")
            # Store only a syntactically valid public IP; never trust arbitrary echo text.
            parsed = ipaddress.ip_address(value)
            if not parsed.is_global:
                raise ValueError("egress service did not return a public IP")
            record["ip"] = str(parsed)
            record["http_status"] = response.status_code
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"[:400]
    return record


def fetch_bytes(
    url: str,
    *,
    allowed_hosts: set[str],
    headers: dict[str, str] | None = None,
    max_bytes: int = 50 * 1024 * 1024,
    timeout: tuple[int, int] = DEFAULT_TIMEOUT,
    attempts: int = DEFAULT_ATTEMPTS,
    expected_status: int = 200,
    expected_content_type: tuple[str, ...] = (),
    pdf: bool = False,
    resume_path: str | pathlib.Path | None = None,
) -> tuple[bytes, dict]:
    """Fetch bounded bytes with HTTP/2 then HTTP/1.1 fallback and resumable partials.

    Partial files are retained only for transport interruptions. Invalid complete
    responses are rejected and their partial bytes discarded. A resumed response
    must honour Content-Range; otherwise the partial is safely restarted.
    """
    validate_official_url(url, allowed_hosts)
    if attempts < 1 or max_bytes < 1:
        raise ValueError("attempts and max_bytes must be positive")

    partial = pathlib.Path(resume_path) if resume_path else None
    if partial:
        partial.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "requested_url": url,
        "started_at_utc": utc_now(),
        "egress_ip": egress_identity(),
        "attempts": [],
    }
    last_error = None

    for attempt in range(1, attempts + 1):
        for protocol, http_version in (
            ("http2", CurlHttpVersion.V2_0),
            ("http1.1", CurlHttpVersion.V1_1),
        ):
            existing = partial.stat().st_size if partial and partial.exists() else 0
            request_headers = dict(headers or {})
            request_headers.setdefault("Accept-Encoding", "identity")
            if existing:
                request_headers["Range"] = f"bytes={existing}-"
            record = {
                "attempt": attempt,
                "protocol": protocol,
                "partial_bytes_before": existing,
                "started_at_utc": utc_now(),
            }
            try:
                mode = "ab" if existing else "wb"
                with curl_requests.Session(impersonate="chrome") as session:
                    response = session.get(
                        url,
                        headers=request_headers,
                        timeout=timeout,
                        stream=True,
                        allow_redirects=True,
                        http_version=http_version,
                    )
                    final_url = str(response.url)
                    validate_official_url(final_url, allowed_hosts)
                    status = response.status_code
                    # A range resume is accepted only for a proper 206 response.
                    if existing and status == 200:
                        existing = 0
                        if partial:
                            partial.unlink(missing_ok=True)
                        request_headers.pop("Range", None)
                        raise RuntimeError("server ignored Range; restart required")
                    if existing and status != 206:
                        raise ValueError(f"resume expected HTTP 206, received {status}")
                    if not existing and status != expected_status:
                        raise ValueError(f"expected HTTP {expected_status}, received {status}")
                    content_range = response.headers.get("Content-Range", "")
                    if existing and not content_range.startswith(f"bytes {existing}-"):
                        raise ValueError("invalid Content-Range for resumed response")
                    content_type = response.headers.get("Content-Type", "")
                    if expected_content_type and not any(
                        item.lower() in content_type.lower() for item in expected_content_type
                    ):
                        raise ValueError(f"unexpected Content-Type: {content_type}")
                    content_length = response.headers.get("Content-Length")
                    expected_total = None
                    if content_length and content_length.isdigit():
                        expected_total = int(content_length) + (existing if status == 206 else 0)
                    if partial:
                        with partial.open(mode) as handle:
                            for chunk in response.iter_content(CHUNK_SIZE):
                                if not chunk:
                                    continue
                                handle.write(chunk)
                                if handle.tell() > max_bytes:
                                    raise ValueError(f"response exceeded {max_bytes} byte cap")
                        body = partial.read_bytes()
                    else:
                        chunks = []
                        received = existing
                        for chunk in response.iter_content(CHUNK_SIZE):
                            if chunk:
                                received += len(chunk)
                                if received > max_bytes:
                                    raise ValueError(f"response exceeded {max_bytes} byte cap")
                                chunks.append(chunk)
                        body = b"".join(chunks)
                    if len(body) > max_bytes:
                        raise ValueError(f"response exceeded {max_bytes} byte cap")
                    if expected_total is not None and len(body) != expected_total:
                        raise IOError(f"incomplete response: expected {expected_total} bytes, got {len(body)}")
                    if pdf:
                        if not body.startswith(b"%PDF"):
                            raise ValueError("response does not start with %PDF")
                        if not body.rstrip().endswith(b"%%EOF"):
                            raise ValueError("PDF is missing terminal %%EOF marker")
                    digest = hashlib.sha256(body).hexdigest()
                    record.update({
                        "http_status": status,
                        "final_url": final_url,
                        "content_type": content_type,
                        "content_length": content_length,
                        "bytes_received": len(body),
                        "sha256": digest,
                        "ok": True,
                        "finished_at_utc": utc_now(),
                    })
                    metadata["attempts"].append(record)
                    metadata.update({
                        "status": "FETCHED_AND_VALIDATED",
                        "final_url": final_url,
                        "http_status": status,
                        "content_type": content_type,
                        "bytes": len(body),
                        "sha256": digest,
                        "finished_at_utc": utc_now(),
                    })
                    if partial:
                        partial.unlink(missing_ok=True)
                    return body, metadata
            except Exception as exc:
                last_error = exc
                record.update({
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}"[:600],
                    "finished_at_utc": utc_now(),
                })
                metadata["attempts"].append(record)
                # A Range-ignored 200 means restart from byte zero immediately.
                if "server ignored Range" in str(exc):
                    break
                # Protocol fallback is attempted before consuming a retry.
                continue
        if attempt < attempts:
            time.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])

    metadata.update({
        "status": "FETCH_FAILED",
        "error": f"{type(last_error).__name__}: {last_error}"[:800] if last_error else "unknown failure",
        "finished_at_utc": utc_now(),
        "partial_bytes_retained": partial.stat().st_size if partial and partial.exists() else 0,
    })
    raise FetchError(metadata)


class FetchError(RuntimeError):
    def __init__(self, metadata: dict):
        self.metadata = metadata
        super().__init__(metadata.get("error", "source fetch failed"))
