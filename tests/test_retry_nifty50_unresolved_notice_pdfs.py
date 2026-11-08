import json
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


def test_cdx_parser_accepts_empty_json_result_as_completed_zero_capture_lookup():
    assert MODULE.parse_cdx_json(b"[]") == []
    assert MODULE.parse_cdx_json("\\ufeff[]") == []


def test_cdx_parser_preserves_header_and_capture_rows():
    payload = b'[["timestamp","original","statuscode","mimetype","digest","length"],["20200101000000","https://example.test/a.pdf","200","application/pdf","ABC","123"]]'
    rows = MODULE.parse_cdx_json(payload)
    assert len(rows) == 2
    assert rows[1][4] == "ABC"


def test_cdx_parser_rejects_non_row_json_with_diagnostic_preview():
    try:
        MODULE.parse_cdx_json(b'{"message":"rate limited"}')
    except ValueError as exc:
        assert "array of rows" in str(exc)
        assert "rate limited" in str(exc)
    else:
        raise AssertionError("non-row CDX JSON accepted")


def test_cdx_variants_cover_original_and_all_official_host_aliases_without_duplicates():
    original = MODULE.DOCUMENTS["NSE-ARCHIVE-2018-06-05-209df26d1951"]
    urls = MODULE.cdx_url_variants(original)
    assert urls[0] == original
    assert len(urls) == 4
    assert len(urls) == len(set(urls))
    assert "nsearchives.nseindia.com" in urls[1]
    assert "archives.nseindia.com" in urls[2]


def test_cdx_capture_rows_handles_header_and_headerless_responses():
    header = ["timestamp", "original", "statuscode", "mimetype", "digest", "length"]
    capture = ["20200101000000", "https://example.test/a.pdf", "200", "application/pdf", "ABC", "123"]
    assert MODULE.cdx_capture_rows([header, capture]) == [capture]
    assert MODULE.cdx_capture_rows([capture]) == [capture]


def test_domain_wide_cdx_searches_follow_exact_host_variants():
    original = MODULE.DOCUMENTS["NSE-ARCHIVE-2018-06-05-209df26d1951"]
    variants = MODULE.cdx_search_variants(original)
    assert len(variants) == 6
    assert all(x["match_type"] == "exact" for x in variants[:4])
    assert variants[4] == {
        "url": "niftyindices.com", "match_type": "domain",
        "filename": "ind_prs05062018.pdf"
    }
    assert variants[5] == {
        "url": "nseindia.com", "match_type": "domain",
        "filename": "ind_prs05062018.pdf"
    }


def test_domain_cdx_query_filters_to_the_registered_pdf_filename():
    variant = MODULE.cdx_search_variants(
        MODULE.DOCUMENTS["NSE-ARCHIVE-2018-06-05-209df26d1951"]
    )[-2]
    params = MODULE.cdx_request_params(variant)
    assert params["matchType"] == "domain"
    assert params["filter"] == [
        "statuscode:200", "original:.*ind_prs05062018\\.pdf$"
    ]


def test_failed_domain_cdx_query_remains_incomplete_and_resumable():
    original = MODULE.DOCUMENTS["NSE-ARCHIVE-2019-07-16-3a8719394912"]
    variants = MODULE.cdx_search_variants(original)
    queries = [
        {"url": variant["url"], "match_type": variant["match_type"],
         "http_status": 200, "result": "EMPTY"}
        for variant in variants[:4]
    ]
    queries.extend([
        {"url": variants[4]["url"], "match_type": "domain",
         "http_status": 503, "result": "HTTP_ERROR"},
        {"url": variants[5]["url"], "match_type": "domain",
         "http_status": 503, "result": "HTTP_ERROR"},
    ])
    item = {"cdx_search_variants": variants, "cdx_queries": queries,
            "cdx_captures": [], "next_cdx_search_index": 6,
            "cdx_checked": True, "cdx_result": "EMPTY"}
    MODULE.reconcile_cdx_search_progress(item)
    assert item["next_cdx_search_index"] == 4
    assert item["cdx_checked"] is False
    assert item["cdx_result"] == "SEARCH_INCOMPLETE"


def test_empty_cdx_is_only_final_after_every_variant_has_valid_response():
    original = MODULE.DOCUMENTS["NSE-ARCHIVE-2018-06-05-209df26d1951"]
    variants = MODULE.cdx_search_variants(original)
    item = {
        "cdx_search_variants": variants,
        "cdx_queries": [
            {"url": variant["url"], "match_type": variant["match_type"],
             "http_status": 200, "result": "EMPTY"}
            for variant in variants
        ],
        "cdx_captures": [],
    }
    MODULE.reconcile_cdx_search_progress(item)
    assert item["next_cdx_search_index"] == len(variants)
    assert item["cdx_checked"] is True
    assert item["cdx_result"] == "EMPTY"


def test_malformed_http_200_cdx_response_does_not_complete_variant():
    original = MODULE.DOCUMENTS["NSE-ARCHIVE-2023-03-14-5b13b76a2af9"]
    variants = MODULE.cdx_search_variants(original)
    item = {
        "cdx_search_variants": variants,
        "cdx_queries": [
            {"url": variant["url"], "match_type": variant["match_type"],
             "http_status": 200, "result": "EMPTY"}
            for variant in variants[:4]
        ] + [{"url": variants[4]["url"], "match_type": "domain",
              "http_status": 200, "result": "INVALID_RESPONSE"}],
        "cdx_captures": [],
    }
    MODULE.reconcile_cdx_search_progress(item)
    assert item["next_cdx_search_index"] == 4
    assert item["cdx_checked"] is False
    assert item["cdx_result"] == "SEARCH_INCOMPLETE"


def test_load_state_reopens_stale_unavailable_notice_when_cdx_search_is_incomplete(tmp_path, monkeypatch):
    doc_id, original = next(iter(MODULE.DOCUMENTS.items()))
    variants = MODULE.cdx_search_variants(original)
    queries = [
        {"url": variant["url"], "match_type": variant.get("match_type", "exact"),
         "http_status": 200, "result": "EMPTY"}
        for variant in variants[:4]
    ]
    queries.append({
        "url": variants[4]["url"], "match_type": "domain",
        "http_status": 503, "result": "HTTP_ERROR",
    })
    state_path = tmp_path / "notice-state.json"
    state_path.write_text(json.dumps({
        "schema_version": 1,
        "documents": {
            doc_id: {
                "original_url": original,
                "direct_urls": MODULE.direct_fallbacks(original),
                "next_direct_index": len(MODULE.direct_fallbacks(original)),
                "cdx_search_variants": variants,
                "cdx_queries": queries,
                "cdx_captures": [],
                "next_cdx_search_index": 4,
                "cdx_checked": False,
                "cdx_result": "SEARCH_INCOMPLETE",
                "status": "DOCUMENT_UNAVAILABLE",
                "unavailable_reason": "stale terminal status from an earlier run",
            }
        },
        "attempt_log": [],
    }), encoding="utf-8")
    monkeypatch.setattr(MODULE, "STATE_PATH", state_path)

    state = MODULE.load_state()
    item = state["documents"][doc_id]

    assert item["cdx_checked"] is False
    assert item["cdx_result"] == "SEARCH_INCOMPLETE"
    assert item["status"] == "PENDING"
    assert "unavailable_reason" not in item
    assert item["classification"] == "UNCLASSIFIED_PENDING_PRIMARY_DOCUMENT_REVIEW"
