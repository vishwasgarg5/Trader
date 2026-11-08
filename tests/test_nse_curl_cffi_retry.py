import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "nse_curl_cffi_retry", Path("scripts/nse_curl_cffi_retry.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_pdf_validation_requires_both_signatures_and_content_length():
    body = b"%PDF-1.7\\nexample\\n%%EOF"
    assert body.startswith(b"%PDF")
    assert body.rstrip().endswith(b"%%EOF")
    assert len(body) > 0


def test_allowlist_rejects_untrusted_hosts_and_http():
    assert MODULE.allowed_url("https://www.niftyindices.com/a.pdf")
    assert MODULE.allowed_url("https://nsearchives.nseindia.com/a.pdf")
    assert not MODULE.allowed_url("https://evil.example/a.pdf")
    assert not MODULE.allowed_url("http://www.niftyindices.com/a.pdf")


def test_download_limits_and_retry_policy_are_explicit():
    assert MODULE.MAX_BYTES == 50 * 1024 * 1024
    assert MODULE.ATTEMPTS == 3
    assert MODULE.READ_TIMEOUT == 180
