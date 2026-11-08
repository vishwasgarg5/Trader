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


def test_pdf_acquisition_delegates_to_shared_fetcher(monkeypatch, tmp_path):
    calls = []
    body = b"%PDF-1.7\\nbody\\n%%EOF"
    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        return body, {"final_url": url, "sha256": "a" * 64, "content_type": "application/pdf"}
    monkeypatch.setattr(MODULE, "fetch_bytes", fake_fetch)
    monkeypatch.setattr(MODULE, "ARCHIVE", tmp_path)
    record, failure = MODULE.download_one(("https://www.nseindia.com/a.pdf", "NSE_TEST", "NSE"))
    assert failure is None
    assert record["sha256"] == "a" * 64
    assert calls[0][1]["pdf"] is True
    assert calls[0][1]["attempts"] == 3


def test_nse_official_document_archive_host_is_allowlisted():
    assert "archives.nseindia.com" in MODULE.ALLOWED_HOSTS
    assert MODULE.safe_pdf_url(
        "https://www.nseindia.com/profile",
        "https://archives.nseindia.com/content/indices/Method_Nifty_50.pdf",
    ) == "https://archives.nseindia.com/content/indices/Method_Nifty_50.pdf"
