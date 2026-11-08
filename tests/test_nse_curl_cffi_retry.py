import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "nse_curl_cffi_retry", Path("scripts/nse_curl_cffi_retry.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_pdf_validation_requires_header_eof_and_matching_content_length():
    body = b"%PDF-1.7\nexample\n%%EOF"
    MODULE.validate_pdf(body, str(len(body)))
    for invalid in (b"not a pdf\n%%EOF", b"%PDF-1.7\ntruncated"):
        try:
            MODULE.validate_pdf(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid PDF body was accepted")
    try:
        MODULE.validate_pdf(body, str(len(body) + 1))
    except ValueError as exc:
        assert "Content-Length mismatch" in str(exc)
    else:
        raise AssertionError("Content-Length mismatch was accepted")


def test_allowlist_rejects_untrusted_hosts_and_http():
    assert MODULE.allowed_url("https://www.niftyindices.com/a.pdf")
    assert MODULE.allowed_url("https://nsearchives.nseindia.com/a.pdf")
    assert not MODULE.allowed_url("https://evil.example/a.pdf")
    assert not MODULE.allowed_url("http://www.niftyindices.com/a.pdf")


def test_download_limits_and_retry_policy_are_explicit():
    assert MODULE.MAX_BYTES == 50 * 1024 * 1024
    assert MODULE.ATTEMPTS == 3
    assert MODULE.READ_TIMEOUT == 180


def test_wayback_cdx_and_nsearchives_transport_checks_are_both_configured():
    source = Path("scripts/nse_curl_cffi_retry.py").read_text()
    assert "web.archive.org/cdx/search/cdx" in source
    assert 'transport_check("https://nsearchives.nseindia.com/content/indices/ind_nifty50.pdf", "requests")' in source
    assert 'transport_check("https://nsearchives.nseindia.com/content/indices/ind_nifty50.pdf", "curl_cffi")' in source
    assert "wayback_future = pool.submit(ingest_wayback)" in source


def test_wayback_targets_include_official_historical_constituent_files():
    targets = MODULE.wayback_targets()
    assert "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv" in targets
    assert "https://archives.nseindia.com/content/indices/ind_nifty50list.csv" in targets
    assert "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv" in targets
    assert "https://www.nseindia.com/content/indices/IndexInclExcl.xls" in targets


def test_wayback_snapshot_url_is_limited_to_dated_allowlisted_csv():
    target = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
    assert MODULE.wayback_snapshot_url("20200601000000", target) == (
        "https://web.archive.org/web/20200601000000id_/" + target
    )
    for timestamp, original in (
        ("2020-06-01", target),
        ("20200601000000", "https://evil.example/constituents.csv"),
        ("20200601000000", "http://evil.example/constituents.csv"),
    ):
        try:
            MODULE.wayback_snapshot_url(timestamp, original)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe or undated Wayback snapshot URL was accepted")


def test_constituent_snapshot_validation_requires_50_symbols_and_valid_isins():
    rows = ["Company Name,Industry,Symbol,Series,ISIN Code"]
    rows.extend(
        f"Company {i},Industry,SYMBOL{i},EQ,INE{i:09d}"
        for i in range(50)
    )
    result = MODULE.validate_constituent_snapshot(("\n".join(rows) + "\n").encode())
    assert result["exactly_50_distinct_symbols"] is True
    assert result["all_rows_have_valid_isin"] is True
    assert result["distinct_symbol_count"] == 50
    invalid = ("Company Name,Industry,Symbol,Series\nA,Industry,AAA,EQ\n").encode()
    try:
        MODULE.validate_constituent_snapshot(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("snapshot without ISIN was accepted")


def test_wayback_snapshot_archiver_records_only_validated_candidates(monkeypatch, tmp_path):
    target = "http://www.niftyindices.com:80/IndexConstituent/ind_nifty50list.csv"
    monkeypatch.setattr(MODULE, "WAYBACK_SNAPSHOT_ARCHIVE", tmp_path)
    rows = ["timestamp", "original", "statuscode", "mimetype", "digest", "length"]

    csv_rows = ["Company Name,Industry,Symbol,Series,ISIN Code"]
    csv_rows.extend(f"Company {i},Industry,SYMBOL{i},EQ,INE{i:09d}" for i in range(50))
    payload = ("\n".join(csv_rows) + "\n").encode()
    cdx_digest = MODULE.wayback_cdx_sha1_digest(payload)
    rows = [rows, ["20200601000000", target, "200", "application/octet-stream", cdx_digest, str(len(payload))]]

    class Response:
        status_code = 200
        content = payload

    class Session:
        def get(self, url, **kwargs):
            assert url == MODULE.wayback_snapshot_url("20200601000000", target)
            return Response()

    result = MODULE.archive_wayback_constituent_snapshots(Session(), target, rows)
    assert len(result) == 1
    assert result[0]["status"] == "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"
    assert result[0]["validation"]["distinct_symbol_count"] == 50
    assert result[0]["cdx_sha1_verified"] is True
    assert (tmp_path / result[0]["archive_path"].split("/")[-1]).exists()


def test_wayback_cdx_json_parser_accepts_array_of_rows_and_rejects_other_shapes():
    payload = '[["timestamp","original"],["20200601000000","https://example.com/a.csv"]]'
    assert MODULE.parse_cdx_json(payload)[1][0] == "20200601000000"
    for invalid in ('not json', '{"rows": []}', '[]'):
        try:
            MODULE.parse_cdx_json(invalid)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid CDX response shape was accepted")


def test_legacy_http_wayback_capture_is_allowlisted_without_enabling_live_http():
    legacy = "http://www.niftyindices.com:80/IndexConstituent/ind_nifty50list.csv"
    assert not MODULE.allowed_url(legacy)
    assert legacy in MODULE.wayback_targets()
    assert MODULE.wayback_snapshot_url("20180530101725", legacy) == (
        "https://web.archive.org/web/20180530101725id_/" + legacy
    )
    try:
        MODULE.wayback_snapshot_url("20180530101725", "http://www.niftyindices.com/other.csv")
    except ValueError:
        pass
    else:
        raise AssertionError("unlisted HTTP Wayback original URL was accepted")


def test_wayback_cdx_sha1_digest_is_verified():
    payload = b"official archived csv bytes\\n"
    digest = MODULE.wayback_cdx_sha1_digest(payload)
    assert len(digest) == 32
    assert MODULE.verify_wayback_cdx_digest(payload, digest) == digest
    try:
        MODULE.verify_wayback_cdx_digest(payload, "A" * 32)
    except ValueError as exc:
        assert "digest mismatch" in str(exc)
    else:
        raise AssertionError("mismatched CDX digest was accepted")


def test_wayback_snapshot_retries_429_with_identity_encoding_and_bounded_backoff(monkeypatch, tmp_path):
    target = "http://www.niftyindices.com:80/IndexConstituent/ind_nifty50list.csv"
    monkeypatch.setattr(MODULE, "WAYBACK_SNAPSHOT_ARCHIVE", tmp_path)
    waits = []
    monkeypatch.setattr(MODULE.time, "sleep", waits.append)
    csv_rows = ["Company Name,Industry,Symbol,Series,ISIN Code"]
    csv_rows.extend(f"Company {i},Industry,SYMBOL{i},EQ,INE{i:09d}" for i in range(50))
    payload = ("\\n".join(csv_rows) + "\\n").encode()
    digest = MODULE.wayback_cdx_sha1_digest(payload)
    cdx_rows = [
        ["timestamp", "original", "statuscode", "mimetype", "digest", "length"],
        ["20180530101725", target, "200", "application/octet-stream", digest, str(len(payload))],
    ]

    class Response:
        def __init__(self, status_code, content=b"", headers=None):
            self.status_code = status_code
            self.content = content
            self.headers = headers or {}

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if len(self.calls) == 1:
                return Response(429)
            return Response(200, payload)

    session = Session()
    result = MODULE.archive_wayback_constituent_snapshots(session, target, cdx_rows)
    assert len(session.calls) == 2
    assert session.calls[0][1]["headers"]["Accept-Encoding"] == "identity"
    assert session.calls[0][1]["headers"]["Cache-Control"] == "no-cache"
    assert waits == [10]
    assert result[0]["fetch_attempts"] == 2
    assert result[0]["retry_wait_seconds"] == [10]
    assert result[0]["cdx_sha1_verified"] is True
    assert result[0]["status"] == "50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW"
