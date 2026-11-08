import csv
import hashlib
import json
from pathlib import Path

from scripts.build_nifty50_anchor_matching_packet import build_packet, decode_cdx_digest
import base64


def _snapshot(path: Path, symbols: list[str]) -> tuple[str, str]:
    payload = "Symbol,ISIN\n" + "".join(f"{symbol},INE0000000000\n" for symbol in symbols)
    raw = payload.encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), base64.b32encode(hashlib.sha1(raw).digest()).decode().rstrip("=")


def test_decode_cdx_digest_returns_raw_sha1_bytes():
    raw = b"payload"
    token = base64.b32encode(hashlib.sha1(raw).digest()).decode().rstrip("=")
    assert decode_cdx_digest(token) == hashlib.sha1(raw).digest()


def test_matching_packet_matches_anchor_differences_to_sample_register_only(tmp_path):
    first = [f"S{i:02d}" for i in range(50)]
    second = first[1:] + ["NEWCO"]
    p1, p2 = tmp_path / "a.csv", tmp_path / "b.csv"
    sha1, cdx1 = _snapshot(p1, first)
    sha2, cdx2 = _snapshot(p2, second)
    state = {"completed_snapshots": [
        {"status": "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW",
         "archive_path": "a.csv", "sha256": sha1, "cdx_digest": cdx1,
         "cdx_digest_validation": "MATCH", "capture_timestamp": "20200101000000",
         "quarter": "2020-Q1", "original_url": "https://example.com/a.csv",
         "validation": {"distinct_symbol_count": 50, "isin_status": "HAS_ISIN"}},
        {"status": "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW",
         "archive_path": "b.csv", "sha256": sha2, "cdx_digest": cdx2,
         "cdx_digest_validation": "MATCH", "capture_timestamp": "20200401000000",
         "quarter": "2020-Q2", "original_url": "https://example.com/a.csv",
         "validation": {"distinct_symbol_count": 50, "isin_status": "HAS_ISIN"}},
    ]}
    transitions = [{"transition_id": "T1", "symbol": "NEWCO", "action": "ADD",
                    "effective_date": "2020-02-01", "verification_status": "SAMPLE_ONLY"}]
    packet = build_packet(state, transitions, tmp_path)
    assert packet["anchor_count"] == 2
    pair = packet["adjacent_anchor_comparisons"][0]
    assert pair["observed_snapshot_changes"] == [
        {"symbol": "NEWCO", "action": "ADD"},
        {"symbol": "S00", "action": "REMOVE"},
    ]
    assert pair["observed_changes_with_register_candidate"][0]["symbol"] == "NEWCO"
    assert pair["observed_changes_without_register_candidate"][0]["symbol"] == "S00"
    assert pair["registered_events_in_window"][0]["verification_status"] == "SAMPLE_ONLY"


def test_matching_packet_rejects_payload_if_cdx_digest_does_not_match(tmp_path):
    symbols = [f"S{i:02d}" for i in range(50)]
    path = tmp_path / "a.csv"
    sha, cdx = _snapshot(path, symbols)
    state = {"completed_snapshots": [{
        "status": "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW",
        "archive_path": "a.csv", "sha256": sha, "cdx_digest": "A" * 32,
        "cdx_digest_validation": "MATCH", "capture_timestamp": "20200101000000",
        "quarter": "2020-Q1", "original_url": "https://example.com/a.csv",
        "validation": {"distinct_symbol_count": 50},
    }]}
    packet = build_packet(state, [], tmp_path)
    assert packet["anchor_count"] == 0
    assert len(packet["rejected_or_alternate_candidates"]) == 1
