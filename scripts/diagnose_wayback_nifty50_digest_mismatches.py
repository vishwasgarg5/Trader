#!/usr/bin/env python3
"""Re-fetch and diagnose Wayback CDX digest mismatches without accepting them."""
from __future__ import annotations

import argparse
import base64
import hashlib
import gzip
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data/reference/wayback_nifty50_acquisition_state.json"
OUTPUT_PATH = ROOT / "data/reports/nifty50_wayback_digest_diagnostics.json"
CDX_URL = "https://web.archive.org/cdx/search/cdx"
USER_AGENT = "Trader-NIFTY50-Digest-Diagnostic/1.0 (+https://github.com/vishwasgarg5/Trader)"
TIMEOUT = (15, 45)
MAX_BYTES = 5 * 1024 * 1024


def decode_digest(value: str) -> bytes:
    token = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z2-7]{32}", token):
        raise ValueError(f"invalid CDX base32 SHA-1 digest: {value!r}")
    decoded = base64.b32decode(token + "=" * ((8 - len(token) % 8) % 8))
    if len(decoded) != 20:
        raise ValueError("CDX digest must decode to 20 SHA-1 bytes")
    return decoded


def digest_matches(payload: bytes, expected: str) -> bool:
    return hashlib.sha1(payload).digest() == decode_digest(expected)


def cdx_records(session: requests.Session, item: dict) -> list[dict]:
    response = session.get(CDX_URL, params={
        "url": item["original_url"],
        "output": "json",
        "filter": "statuscode:200",
        "from": item["capture_timestamp"][:4],
        "to": item["capture_timestamp"][:4],
        "fl": "timestamp,original,statuscode,mimetype,digest,length,type",
    }, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}, timeout=TIMEOUT)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], list):
        raise ValueError("unexpected CDX JSON response")
    headers = rows[0]
    required = {"timestamp", "original", "statuscode", "mimetype", "digest", "length"}
    if not required.issubset(headers):
        raise ValueError(f"CDX response missing fields: {sorted(required - set(headers))}")
    return [dict(zip(headers, row)) for row in rows[1:] if len(row) == len(headers)]


def fetch_capture(session: requests.Session, record: dict, expected: str) -> dict:
    url = f"https://web.archive.org/web/{record['timestamp']}id_/{record['original']}"
    response = session.get(url, headers={"User-Agent": USER_AGENT,
        "Accept-Encoding": "identity"}, timeout=TIMEOUT, stream=True)
    wire_payload = b""
    decoded_payload = b""
    encoding = (response.headers.get("Content-Encoding") or "").lower()
    if response.status_code == 200:
        # requests.Response.content transparently decompresses Content-Encoding.
        # CDX digest/length may refer to the stored encoded payload, so retain and
        # compare the undecoded entity bytes separately from the CSV bytes.
        response.raw.decode_content = False
        wire_payload = response.raw.read(MAX_BYTES + 1)
        if len(wire_payload) > MAX_BYTES:
            raise ValueError("Wayback replay exceeds diagnostic byte cap")
        if "gzip" in encoding:
            decoded_payload = gzip.decompress(wire_payload)
        else:
            decoded_payload = wire_payload
    response.close()
    wire_digest = (base64.b32encode(hashlib.sha1(wire_payload).digest()).decode("ascii").rstrip("=")
                   if wire_payload else None)
    decoded_digest = (base64.b32encode(hashlib.sha1(decoded_payload).digest()).decode("ascii").rstrip("=")
                      if decoded_payload else None)
    return {
        "timestamp": record["timestamp"],
        "original_url": record["original"],
        "capture_type": record.get("type") or "NOT_EXPOSED_BY_CDX",
        "mimetype": record.get("mimetype"),
        "cdx_digest": expected,
        "cdx_length": record.get("length"),
        "http_status": response.status_code,
        "wire_bytes_received": len(wire_payload),
        "decoded_bytes_received": len(decoded_payload),
        "wire_computed_digest": wire_digest,
        "decoded_computed_digest": decoded_digest,
        "wire_digest_match": bool(wire_payload) and digest_matches(wire_payload, expected),
        "decoded_digest_match": bool(decoded_payload) and digest_matches(decoded_payload, expected),
        "digest_match": bool(wire_payload) and digest_matches(wire_payload, expected),
        "memento_datetime": response.headers.get("Memento-Datetime"),
        "content_encoding": encoding or None,
        "response_url": response.url,
    }


def diagnose(state: dict, session: requests.Session, pause_seconds: float = 3.0) -> dict:
    mismatches = [x for x in state.get("completed_snapshots", [])
                  if x.get("status") == "CDX_DIGEST_MISMATCH"]
    results = []
    for item in mismatches:
        expected = item.get("cdx_digest", "")
        decode_digest(expected)
        record = {
            "timestamp": item["capture_timestamp"],
            "original": item["original_url"],
            "statuscode": "200",
            "digest": expected,
            "length": item.get("cdx_length", ""),
            "mimetype": item.get("mimetype", ""),
            "type": "NOT_EXPOSED_IN_SAVED_METADATA",
        }
        try:
            records = cdx_records(session, item)
            same = [r for r in records if r.get("digest") == expected
                    and r.get("original") == item["original_url"]
                    and r.get("statuscode") == "200"]
            exact = next((r for r in same if r.get("timestamp") == item["capture_timestamp"]), None)
            neighbours = [r for r in same if r.get("timestamp") != item["capture_timestamp"]]
            neighbours.sort(key=lambda r: abs(int(r["timestamp"]) - int(item["capture_timestamp"])))
            selected = []
            if exact:
                selected.extend([exact, exact])  # independent repeat fetch of exact memento
            if neighbours:
                selected.append(neighbours[0])
            attempts = []
            for index, capture in enumerate(selected):
                if index:
                    time.sleep(pause_seconds)
                try:
                    attempts.append(fetch_capture(session, capture, expected))
                except requests.RequestException as exc:
                    attempts.append({"timestamp": capture["timestamp"],
                                     "error": f"{type(exc).__name__}: {exc}"})
            results.append({
                "quarter": item.get("quarter"),
                "timestamp": item["capture_timestamp"],
                "original_url": item["original_url"],
                "expected_digest": expected,
                "decoded_expected_sha1_hex": decode_digest(expected).hex(),
                "same_digest_capture_count": len(same),
                "exact_capture_found": exact is not None,
                "neighbour_capture_timestamp": neighbours[0]["timestamp"] if neighbours else None,
                "attempts": attempts,
                "decision": (
                    "CDX_DIGEST_MATCHED_ON_RAW_REPLAY_BYTES; PERSIST_AND_REVALIDATE_BEFORE_STATE_ACCEPTANCE"
                    if any(a.get("wire_digest_match") or a.get("digest_match") for a in attempts)
                    else "REMAIN_QUARANTINED_UNLESS_A_FETCH_MATCHES_CDX_DIGEST"
                ),
            })
        except Exception as exc:
            results.append({
                "quarter": item.get("quarter"),
                "timestamp": item["capture_timestamp"],
                "original_url": item["original_url"],
                "expected_digest": expected,
                "decoded_expected_sha1_hex": decode_digest(expected).hex(),
                "error": f"{type(exc).__name__}: {exc}",
                "decision": "REMAIN_QUARANTINED",
            })
    return {
        "schema_version": 1,
        "report_type": "WAYBACK_CDX_DIGEST_MISMATCH_DIAGNOSTICS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mismatch_count": len(mismatches),
        "results": results,
        "limitations": [
            "This diagnostic never modifies the acquisition state or accepts a snapshot.",
            "Only a byte-for-byte payload whose SHA-1 matches the decoded CDX digest may be accepted.",
            "A revisit record is reported as such when CDX exposes its type; the fetched replay body is still digest-checked.",
            "A neighbouring capture is diagnostic evidence only and must independently pass the digest check.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=STATE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    state_payload = args.state.read_bytes()
    report = diagnose(json.loads(state_payload), session)
    report["input_state_sha256"] = hashlib.sha256(state_payload).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"mismatches": report["mismatch_count"],
                      "results": len(report["results"]), "output": args.output.as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
