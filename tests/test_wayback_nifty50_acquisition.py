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


def test_quarter_matrix_has_28_quarters():
    assert len(MODULE.all_quarters()) == 28
    assert MODULE.all_quarters()[0] == "2018-Q1"
    assert MODULE.all_quarters()[-1] == "2024-Q4"
