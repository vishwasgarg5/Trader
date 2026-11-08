import base64
import hashlib
import json
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "wayback_nifty50_acquisition", Path("scripts/wayback_nifty50_acquisition.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_targets_cover_all_requested_hosts_and_legacy_nse_host():
    assert len(MODULE.TARGETS) == 6
    assert any("www1.nseindia.com" in x for x in MODULE.TARGETS)
    assert any("www.nseindia.com" in x for x in MODULE.TARGETS)
    assert any("www.niftyindices.com" in x for x in MODULE.TARGETS)
    assert any("nsearchives.nseindia.com" in x for x in MODULE.TARGETS)
    assert any("archives.nseindia.com" in x for x in MODULE.TARGETS)


def test_snapshot_validation_accepts_schema_without_isin():
    rows = ["Company Name,Industry,Symbol,Series"]
    rows.extend(f"Company {i},Industry,SYM{i},EQ" for i in range(50))
    result = MODULE.validate_snapshot(("\n".join(rows) + "\n").encode())
    assert result["distinct_symbol_count"] == 50
    assert result["isin_status"] == "NO_ISIN"
    assert result["normalized_header_mapping"]["symbol"] == "Symbol"


def test_snapshot_validation_normalizes_historical_headers_and_retains_non_50():
    rows = ["Security Name,Trading Symbol,ISIN No."]
    rows.extend(f"Company {i},SYM{i},INE{i:09d}" for i in range(49))
    result = MODULE.validate_snapshot(("\n".join(rows) + "\n").encode())
    assert result["isin_status"] == "HAS_ISIN"
    assert result["distinct_symbol_count"] == 49
    assert result["candidate_status"] == "NON_50_SNAPSHOT_REQUIRES_REVIEW"


def test_snapshot_validation_rejects_implausible_counts_and_html():
    try:
        MODULE.validate_snapshot(b"<html>blocked</html>")
    except ValueError:
        pass
    else:
        raise AssertionError("HTML response accepted")
    try:
        MODULE.validate_snapshot(b"Symbol\nONLYONE\n")
    except ValueError:
        pass
    else:
        raise AssertionError("implausible snapshot accepted")


def test_cdx_requests_include_status_filter_and_digest_collapse_only_for_candidate_query():
    full = MODULE.cdx_params(MODULE.TARGETS[0], False)
    collapsed = MODULE.cdx_params(MODULE.TARGETS[0], True)
    assert full["filter"] == "statuscode:200"
    assert "collapse" not in full
    assert collapsed["collapse"] == "digest"
    assert full["from"] == "2018" and full["to"] == "2024"


def test_snapshot_url_requires_allowlisted_target_and_timestamp():
    target = MODULE.TARGETS[0]
    assert MODULE.snapshot_url("20200101000000", target).endswith(target)
    for ts, url in [("2020", target), ("20200101000000", "https://evil.example/a.csv")]:
        try:
            MODULE.snapshot_url(ts, url)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe snapshot URL accepted")


def test_wayback_cdx_digest_matches_base32_sha1_body_digest():
    payload = b"sample archived CSV bytes\\n"
    expected = base64.b32encode(hashlib.sha1(payload).digest()).decode("ascii").rstrip("=")
    assert MODULE.wayback_cdx_digest(payload) == expected
    assert MODULE.cdx_digest_matches(payload, expected)
    assert not MODULE.cdx_digest_matches(payload, "A" * 32)


def test_retry_after_supports_seconds_and_http_date():
    assert MODULE.parse_retry_after("12") == 12
    assert MODULE.parse_retry_after(None) is None



def test_capture_target_accepts_http_default_port_variant_without_widening_allowlist():
    target = MODULE.TARGETS[0]
    archived_original = "http://www.niftyindices.com:80/IndexConstituent/ind_nifty50list.csv"
    assert MODULE.capture_matches_target(archived_original, target)
    assert not MODULE.capture_matches_target(
        "https://evil.example/IndexConstituent/ind_nifty50list.csv", target
    )
    assert not MODULE.capture_matches_target(
        "https://www.niftyindices.com/other.csv", target
    )
    assert MODULE.snapshot_url("20180128030056", archived_original).endswith(archived_original)


def test_collapsed_capture_queue_accepts_http_default_port_variant_idempotently():
    target = MODULE.TARGETS[0]
    original = "http://www.niftyindices.com:80/IndexConstituent/ind_nifty50list.csv"
    rows = [[
        "timestamp", "original", "statuscode", "mimetype", "digest", "length"
    ], [
        "20180128030056", original, "200", "application/octet-stream",
        "KH6SOBBVQ5CRSCCU6GDS4CPXBSCMCSXM", "1735"
    ]]
    state = {"pending_snapshots": [], "completed_snapshots": []}
    assert MODULE.add_collapsed_captures(state, target, rows) == 1
    assert state["pending_snapshots"][0]["original_url"] == original
    assert MODULE.add_collapsed_captures(state, target, rows) == 0


def test_quarter_matrix_has_28_quarters():
    assert len(MODULE.all_quarters()) == 28
    assert MODULE.all_quarters()[0] == "2018-Q1"
    assert MODULE.all_quarters()[-1] == "2024-Q4"



def test_load_state_revalidates_existing_snapshot_cdx_digests(tmp_path, monkeypatch):
    matching_bytes = b"verified archived snapshot bytes\\n"
    mismatching_bytes = b"replayed bytes that do not match CDX\\n"
    matching_path = tmp_path / "matching.csv"
    mismatching_path = tmp_path / "mismatching.csv"
    matching_path.write_bytes(matching_bytes)
    mismatching_path.write_bytes(mismatching_bytes)

    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "schema_version": 1,
        "targets": {},
        "pending_snapshots": [],
        "completed_snapshots": [
            {
                "archive_path": str(matching_path),
                "cdx_digest": MODULE.wayback_cdx_digest(matching_bytes),
                "status": "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW",
            },
            {
                "archive_path": str(mismatching_path),
                "cdx_digest": "A" * 32,
                "status": "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW",
            },
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(MODULE, "STATE_PATH", state_path)

    state = MODULE.load_state()
    matching, mismatching = state["completed_snapshots"]

    assert matching["cdx_digest_validation"] == "MATCH"
    assert matching["status"] == "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"
    assert mismatching["cdx_digest_validation"] == "MISMATCH"
    assert mismatching["status"] == "CDX_DIGEST_MISMATCH"
    assert mismatching["pre_digest_validation_status"] == "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"

def test_collapsed_capture_queue_accepts_application_csv_mimetype():
    target = MODULE.TARGETS[3]
    original = "https://www.nseindia.com/content/indices/ind_nifty50list.csv"
    rows = [[
        "timestamp", "original", "statuscode", "mimetype", "digest", "length"
    ], [
        "20181028012125", original, "200", "application/csv",
        "QIL3O7JSQCHCJMBPAH4PFUTYR3DZBKLL", "1671"
    ]]
    state = {"pending_snapshots": [], "completed_snapshots": []}
    assert MODULE.add_collapsed_captures(state, target, rows) == 1
    assert state["pending_snapshots"][0]["quarter"] == "2018-Q4"

def test_capture_target_accepts_nse_apex_alias_for_official_www_host():
    target = "https://www.nseindia.com/content/indices/ind_nifty50list.csv"
    assert MODULE.capture_matches_target(
        "https://nseindia.com/content/indices/ind_nifty50list.csv", target
    )
    assert not MODULE.capture_matches_target(
        "https://evil.example/content/indices/ind_nifty50list.csv", target
    )


def test_full_cdx_recovers_one_candidate_for_each_uncovered_quarter():
    shared_digest = "GYG2MUVZFF6WE5UCSPAMYLZTRIZGQLZ6"
    state = {
        "pending_snapshots": [],
        "completed_snapshots": [{
            "capture_timestamp": "20180929103632",
            "original_url": "http://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
            "quarter": "2018-Q3", "cdx_digest": shared_digest,
            "cdx_digest_validation": "MATCH",
            "status": "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW",
        }, {
            "capture_timestamp": "20240819184501",
            "original_url": "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
            "quarter": "2024-Q3", "cdx_digest": "OOKVMLPTG4NXLNGPK6NU5BBFKBIP4OVR",
            "cdx_digest_validation": "MISMATCH", "status": "CDX_DIGEST_MISMATCH",
        }],
    }
    records = [{
        "captures": [
            {"quarter": "2019-Q1", "timestamp": "20190201175058",
             "original_url": "http://niftyindices.com/IndexConstituent/ind_nifty50list.csv",
             "statuscode": "200", "mimetype": "application/octet-stream",
             "digest": shared_digest, "length": "1713"},
            {"quarter": "2024-Q3", "timestamp": "20240701180136",
             "original_url": "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
             "statuscode": "200", "mimetype": "application/octet-stream",
             "digest": "OOKVMLPTG4NXLNGPK6NU5BBFKBIP4OVR", "length": "2232"},
        ],
    }]
    assert MODULE.add_full_metadata_quarter_candidates(state, records) == 2
    assert {item["quarter"] for item in state["pending_snapshots"]} == {
        "2019-Q1", "2024-Q3"
    }
    assert all(item["candidate_source"] == "FULL_CDX_QUARTER_GAP_RECOVERY"
               for item in state["pending_snapshots"])
