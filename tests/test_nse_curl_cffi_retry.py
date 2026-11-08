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
