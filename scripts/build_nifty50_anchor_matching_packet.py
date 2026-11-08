#!/usr/bin/env python3
"""Build a fail-closed comparison packet from verified-digest NIFTY 50 anchors.

The packet is a review aid only. It never writes canonical membership intervals,
changes transition verification states, or authorizes model validation.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "data/reference/wayback_nifty50_acquisition_state.json"
DEFAULT_TRANSITIONS = ROOT / "data/reference/nifty50_transition_register.csv"
DEFAULT_OUTPUT = ROOT / "data/reports/nifty50_anchor_matching_packet.json"
CANDIDATE_STATUS = "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"


def decode_cdx_digest(value: str) -> bytes:
    token = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z2-7]{32}", token):
        raise ValueError(f"invalid 32-character base32 CDX SHA-1 digest: {value!r}")
    decoded = base64.b32decode(token + "=" * ((8 - len(token) % 8) % 8))
    if len(decoded) != 20:
        raise ValueError("CDX digest did not decode to a 20-byte SHA-1")
    return decoded


def read_symbols(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path}: missing CSV header")
        keys = {re.sub(r"[^a-z0-9]", "", key.lower()): key for key in reader.fieldnames}
        symbol_key = next((keys[k] for k in ("symbol", "tradingsymbol", "ticker") if k in keys), None)
        if not symbol_key:
            raise ValueError(f"{path}: no recognized symbol column")
        values = [str(row.get(symbol_key) or "").strip().upper() for row in reader]
    values = [value for value in values if value]
    if len(values) != 50 or len(set(values)) != 50:
        raise ValueError(f"{path}: expected exactly 50 distinct symbols; got {len(set(values))}")
    return sorted(set(values))


def load_verified_anchors(state: dict, root: Path) -> tuple[list[dict], list[dict]]:
    anchors, rejected = [], []
    for item in state.get("completed_snapshots", []):
        if item.get("status") != CANDIDATE_STATUS:
            continue
        path_text = item.get("archive_path", "")
        path = (root / path_text).resolve()
        try:
            path.relative_to(root.resolve())
            payload = path.read_bytes()
            actual_sha256 = hashlib.sha256(payload).hexdigest()
            expected_sha256 = item.get("sha256", "")
            if not expected_sha256 or actual_sha256 != expected_sha256:
                raise ValueError("local SHA-256 does not match acquisition state")
            expected_cdx = decode_cdx_digest(item.get("cdx_digest", ""))
            if hashlib.sha1(payload).digest() != expected_cdx:
                raise ValueError("raw payload does not match decoded CDX SHA-1")
            if item.get("cdx_digest_validation") != "MATCH":
                raise ValueError("acquisition state does not mark CDX digest MATCH")
            symbols = read_symbols(path)
            if item.get("validation", {}).get("distinct_symbol_count") != 50:
                raise ValueError("acquisition validation does not record 50 distinct symbols")
            anchors.append({
                "timestamp": item["capture_timestamp"],
                "as_of_date": date.fromisoformat(
                    f"{item['capture_timestamp'][:4]}-{item['capture_timestamp'][4:6]}-{item['capture_timestamp'][6:8]}"
                ).isoformat(),
                "quarter": item["quarter"],
                "original_url": item["original_url"],
                "archive_path": path_text,
                "sha256": actual_sha256,
                "cdx_digest": item["cdx_digest"],
                "symbols": symbols,
                "isin_status": item.get("validation", {}).get("isin_status", "UNKNOWN"),
                "review_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
            })
        except Exception as exc:
            rejected.append({
                "timestamp": item.get("capture_timestamp"),
                "quarter": item.get("quarter"),
                "archive_path": path_text,
                "reason": f"{type(exc).__name__}: {exc}",
            })
    anchors.sort(key=lambda row: (row["as_of_date"], row["timestamp"]))
    # Keep the latest eligible capture in each quarter; retain other eligible
    # captures as alternate evidence in the packet rather than double-counting.
    selected, alternates = [], []
    for anchor in anchors:
        if selected and selected[-1]["quarter"] == anchor["quarter"]:
            alternates.append(anchor)
            selected[-1] = anchor
        else:
            selected.append(anchor)
    return selected, rejected + [{"timestamp": x["timestamp"], "quarter": x["quarter"],
                                  "archive_path": x["archive_path"],
                                  "reason": "ALTERNATE_CAPTURE_SAME_QUARTER; retained separately"}
                                 for x in alternates]


def load_transition_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_packet(state: dict, transitions: list[dict], root: Path) -> dict:
    anchors, rejected = load_verified_anchors(state, root)
    pairs = []
    for previous, current in zip(anchors, anchors[1:]):
        old, new = set(previous["symbols"]), set(current["symbols"])
        observed = sorted(
            [{"symbol": symbol, "action": "REMOVE"} for symbol in old - new]
            + [{"symbol": symbol, "action": "ADD"} for symbol in new - old],
            key=lambda row: (row["action"], row["symbol"]),
        )
        start, end = previous["as_of_date"], current["as_of_date"]
        window_events = []
        for event in transitions:
            effective = event.get("effective_date", "").strip()
            try:
                in_window = start < date.fromisoformat(effective).isoformat() <= end
            except ValueError:
                in_window = False
            if in_window:
                window_events.append({
                    "transition_id": event.get("transition_id", ""),
                    "symbol": event.get("symbol", "").strip().upper(),
                    "action": event.get("action", "").strip().upper(),
                    "effective_date": effective,
                    "verification_status": event.get("verification_status", ""),
                    "reviewer": event.get("reviewer", ""),
                    "source_url": event.get("source_url", ""),
                    "source_document_path": event.get("source_document_path", ""),
                    "superseding_notice_url": event.get("superseding_notice_url", ""),
                    "notes": event.get("notes", ""),
                })
        expected_keys = {(e["symbol"], e["action"]) for e in window_events}
        observed_keys = {(e["symbol"], e["action"]) for e in observed}
        pairs.append({
            "from_anchor": {k: previous[k] for k in ("quarter", "as_of_date", "timestamp", "sha256")},
            "to_anchor": {k: current[k] for k in ("quarter", "as_of_date", "timestamp", "sha256")},
            "observed_snapshot_changes": observed,
            "registered_events_in_window": window_events,
            "observed_changes_with_register_candidate": [
                {"symbol": s, "action": a,
                 "register_status": "REGISTERED_CANDIDATE_NOT_HUMAN_VERIFIED"}
                for s, a in sorted(observed_keys & expected_keys)
            ],
            "observed_changes_without_register_candidate": [
                {"symbol": s, "action": a, "status": "UNEXPLAINED_REQUIRES_REVIEW"}
                for s, a in sorted(observed_keys - expected_keys)
            ],
            "registered_events_not_visible_in_anchor_difference": [
                {"symbol": s, "action": a, "status": "NOT_VISIBLE_AT_ANCHORS_REQUIRES_DATE_OR_IDENTITY_REVIEW"}
                for s, a in sorted(expected_keys - observed_keys)
            ],
            "pair_status": "REVIEW_REQUIRED",
            "interpretation": (
                "Quarterly snapshots bracket a period, not each event date. "
                "A register-row match is not verification; multiple offsetting events, "
                "special membership phases, and identity changes require primary-source review."
            ),
        })
    return {
        "schema_version": 1,
        "report_type": "NIFTY50_ANCHOR_MATCHING_REVIEW_PACKET",
        "status": "REVIEW_REQUIRED_NOT_CANONICAL",
        "scope": "NIFTY 50 only; 2018-2024",
        "anchor_count": len(anchors),
        "anchor_quarters": [a["quarter"] for a in anchors],
        "anchors": [{k: v for k, v in a.items() if k != "symbols"} | {"symbols": a["symbols"]}
                    for a in anchors],
        "rejected_or_alternate_candidates": rejected,
        "adjacent_anchor_pair_count": len(pairs),
        "adjacent_anchor_comparisons": pairs,
        "transition_register_rows": len(transitions),
        "limitations": [
            "All snapshots remain supplementary candidates pending human review.",
            "Only local files with matching SHA-256 and decoded CDX SHA-1 are admitted.",
            "Register matches inherit their existing verification state; SAMPLE_ONLY is never upgraded.",
            "Quarterly anchor differences do not prove the exact effective date of a transition.",
            "No canonical membership intervals or model inputs are written.",
            "The 2018-Q1 anchor predates the registered research window start of 2018-04-01.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--transitions", type=Path, default=DEFAULT_TRANSITIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    packet = build_packet(json.loads(args.state.read_text(encoding="utf-8")),
                          load_transition_rows(args.transitions), ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": packet["status"],
        "anchors": packet["anchor_count"],
        "pairs": packet["adjacent_anchor_pair_count"],
        "rejected_or_alternate": len(packet["rejected_or_alternate_candidates"]),
        "output": args.output.as_posix(),
    }, indent=2))
    return 0 if packet["anchor_count"] >= 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
