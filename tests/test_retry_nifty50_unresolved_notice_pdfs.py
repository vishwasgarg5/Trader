import importlib.util
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


def test_retry_after_seconds_supported():
    assert MODULE.retry_after("17") == 17
    assert MODULE.retry_after(None) is None
