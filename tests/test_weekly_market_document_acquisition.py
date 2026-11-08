import importlib.util
import pathlib

SPEC = importlib.util.spec_from_file_location(
    "weekly_market_document_acquisition",
    pathlib.Path("scripts/weekly_market_document_acquisition.py"),
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_pdf_link_resolution_allows_only_official_https_pdf_hosts():
    assert MODULE.safe_pdf_url(
        "https://www.nseindia.com/page", "/content/circulars/test.pdf"
    ) == "https://www.nseindia.com/content/circulars/test.pdf"
    assert MODULE.safe_pdf_url(
        "https://www.bseindia.com/page", "https://evil.example/file.pdf"
    ) is None
    assert MODULE.safe_pdf_url(
        "https://www.nseindia.com/page", "http://nseindia.com/file.pdf"
    ) is None
    assert MODULE.safe_pdf_url(
        "https://www.nseindia.com/page", "/page?document=1"
    ) is None


def test_pdf_link_query_and_fragment_are_normalized():
    assert MODULE.safe_pdf_url(
        "https://nsearchives.nseindia.com/x", "/a/circular.pdf?download=1#top"
    ) == "https://nsearchives.nseindia.com/a/circular.pdf?download=1"


def test_pdf_archive_contract_keeps_execution_gates_closed():
    assert MODULE.MAX_BYTES == 25 * 1024 * 1024
    assert "nsearchives.nseindia.com" in MODULE.ALLOWED_HOSTS
    assert "www.bseindia.com" in MODULE.ALLOWED_HOSTS
