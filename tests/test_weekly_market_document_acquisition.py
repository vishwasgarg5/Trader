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


def test_transient_pdf_download_timeout_is_retried(monkeypatch):
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def flaky_urlopen(request, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise TimeoutError("temporary read timeout")
        return Response()

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", flaky_urlopen)
    monkeypatch.setattr(MODULE.time, "sleep", lambda _seconds: None)
    response = MODULE.open_with_retry(object(), timeout=MODULE.TIMEOUT)
    assert isinstance(response, Response)
    assert calls == [MODULE.TIMEOUT, MODULE.TIMEOUT]


def test_nse_official_document_archive_host_is_allowlisted():
    assert "archives.nseindia.com" in MODULE.ALLOWED_HOSTS
    assert MODULE.safe_pdf_url(
        "https://www.nseindia.com/profile",
        "https://archives.nseindia.com/content/indices/Method_Nifty_50.pdf",
    ) == "https://archives.nseindia.com/content/indices/Method_Nifty_50.pdf"
