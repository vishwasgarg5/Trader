import base64
import hashlib
import importlib.util
from types import SimpleNamespace
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "retry_nifty50_unresolved_notice_pdfs", Path("scripts/retry_nifty50_unresolved_notice_pdfs.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_three_unresolved_documents_and_original_urls_are_registered():
    assert len(MODULE.DOCUMENTS) == 3
    assert MODULE.DOCUMENTS["NSE-ARCHIVE-2018-06-05-209df26d1951"].endswith("ind_prs05062018.pdf")
    assert MODULE.DOCUMENTS["NSE-ARCHIVE-2019-07-16-3a8719394912"].endswith("ind_prs16072019_1.pdf")
    assert MODULE.DOCUMENTS["NSE-ARCHIVE-2023-03-14-5b13b76a2af9"].endswith("ind_prs14032023.pdf")


def test_fallback_order_starts_with_nsearchives_then_archive_then_niftyindices():
    urls = MODULE.direct_fallbacks(MODULE.DOCUMENTS["NSE-ARCHIVE-2018-06-05-209df26d1951"])
    assert "nsearchives.nseindia.com" in urls[0]
    assert "archives.nseindia.com" in urls[1]
    assert "www.niftyindices.com" in urls[2]
    assert "niftyindices.com" in urls[3]


def test_pdf_validation_requires_signature_and_eof():
    MODULE.validate_pdf(b"%PDF-1.7\nminimal\n%%EOF\n")
    for bad in (b"not a pdf", b"%PDF-1.7\ntruncated"):
        try:
            MODULE.validate_pdf(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid PDF accepted")


def test_transient_direct_failure_advances_to_next_official_fallback():
    item = {"next_direct_index": 0}
    assert MODULE.advance_direct_fallback(
        item, SimpleNamespace(stop=None), "https://nsearchives.nseindia.com/example.pdf"
    )
    assert item["next_direct_index"] == 1
    assert item["fallback_errors"][0]["reason"] == "request_failed_after_retries"


def test_budget_or_throttle_stop_does_not_advance_notice_fallback():
    item = {"next_direct_index": 2}
    assert not MODULE.advance_direct_fallback(
        item, SimpleNamespace(stop="HTTP_429_THROTTLED"), "https://nsearchives.nseindia.com/example.pdf"
    )
    assert item["next_direct_index"] == 2


def test_legacy_three_timeouts_are_reconciled_to_next_official_host():
    urls = MODULE.direct_fallbacks(MODULE.DOCUMENTS[next(iter(MODULE.DOCUMENTS))])
    item = {"direct_urls": urls, "next_direct_index": 0}
    attempt_log = [
        {"url": urls[0], "attempt": n, "error": "ReadTimeout"}
        for n in (1, 2, 3)
    ]
    assert MODULE.reconcile_exhausted_direct_fallback(item, attempt_log)
    assert item["next_direct_index"] == 1
    assert item["fallback_errors"][0]["reason"] == "migrated_legacy_three_transient_failures"


def test_legacy_fallback_reconciliation_does_not_advance_on_incomplete_or_http_attempts():
    urls = MODULE.direct_fallbacks(MODULE.DOCUMENTS[next(iter(MODULE.DOCUMENTS))])
    item = {"direct_urls": urls, "next_direct_index": 0}
    incomplete = [{"url": urls[0], "attempt": n, "error": "ReadTimeout"} for n in (1, 2)]
    assert not MODULE.reconcile_exhausted_direct_fallback(item, incomplete)
    http_response = [{"url": urls[0], "attempt": 1, "error": "ReadTimeout"},
                     {"url": urls[0], "attempt": 2, "error": "ReadTimeout"},
                     {"url": urls[0], "attempt": 3, "http_status": 404}]
    assert not MODULE.reconcile_exhausted_direct_fallback(item, http_response)
    assert item["next_direct_index"] == 0


def test_retry_after_seconds_supported():
    assert MODULE.retry_after("17") == 17
    assert MODULE.retry_after(None) is None


def test_wayback_cdx_digest_matches_base32_sha1_body():
    payload = b"%PDF-1.7\\nminimal\\n%%EOF\\n"
    expected = base64.b32encode(hashlib.sha1(payload).digest()).decode("ascii").rstrip("=")
    assert MODULE.wayback_cdx_digest(payload) == expected
    assert MODULE.cdx_digest_matches(payload, expected)
    assert MODULE.cdx_digest_matches(payload, expected.lower())
    assert not MODULE.cdx_digest_matches(payload + b"changed", expected)
    assert not MODULE.cdx_digest_matches(payload, "")
