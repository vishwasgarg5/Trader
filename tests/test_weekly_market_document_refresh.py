import hashlib
import importlib.util
import pathlib
import tempfile

SPEC = importlib.util.spec_from_file_location(
    "weekly_market_document_refresh",
    pathlib.Path("scripts/weekly_market_document_refresh.py"),
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_link_parser_extracts_labels_and_relative_urls():
    parser = MODULE.LinkParser()
    parser.feed('<a href="/circulars/abc.pdf">  Dividend&nbsp; Circular </a>')
    assert parser.links == [{"label": "Dividend Circular", "href": "/circulars/abc.pdf"}]


def test_fetch_rejects_non_html(monkeypatch):
    class Headers(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class Response:
        status = 200
        headers = Headers({"Content-Type": "application/pdf", "Last-Modified": None})
        def read(self, limit):
            return b"%PDF-1.7"
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", lambda *a, **k: Response())
    try:
        MODULE.fetch("https://exchange.example/page")
    except ValueError as exc:
        assert "unexpected content type" in str(exc)
    else:
        raise AssertionError("non-HTML response accepted as landing page")


def test_report_schema_contract_keeps_research_safety_explicit():
    assert len(MODULE.SOURCES) >= 6
    assert MODULE.MEMBERSHIP.name == "nifty50_membership.csv"
    assert "BSE" in {"BSE" if item[0].startswith("BSE_") else "NSE" for item in MODULE.SOURCES}
    assert "NSE" in {"NSE" if item[0].startswith("NSE_") else "BSE" for item in MODULE.SOURCES}

def test_current_constituent_csv_requires_exactly_50_unique_symbols():
    body = ("Symbol,Company Name\n" + "".join(
        f"SYM{i},Company {i}\n" for i in range(50)
    )).encode()
    symbols = MODULE.parse_current_constituents(body)
    assert len(symbols) == 50
    assert len(set(symbols)) == 50


def test_current_constituent_csv_rejects_duplicates_and_wrong_count():
    duplicate = ("Symbol\n" + "SAME\n" * 50).encode()
    try:
        MODULE.parse_current_constituents(duplicate)
    except ValueError as exc:
        assert "50 unique" in str(exc)
    else:
        raise AssertionError("duplicate symbols accepted")

    short = ("Symbol\n" + "".join(f"SYM{i}\n" for i in range(49))).encode()
    try:
        MODULE.parse_current_constituents(short)
    except ValueError as exc:
        assert "received 49 rows" in str(exc)
    else:
        raise AssertionError("49-row constituent file accepted")


def test_constituent_snapshot_is_explicitly_not_historical_membership():
    assert "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv" == MODULE.CONSTITUENT_URL
    assert MODULE.TIMEOUT_SECONDS == 45
    assert MODULE.RETRY_ATTEMPTS == 3


def test_constituent_acquisition_reports_50_rows_without_name_error(monkeypatch, tmp_path):
    class Headers(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class Response:
        headers = Headers({"Content-Type": "text/csv"})
        def geturl(self):
            return MODULE.CONSTITUENT_URL
        def read(self, limit):
            return ("Symbol,Company Name\\n" + "".join(
                f"SYM{i},Company {i}\\n" for i in range(50)
            )).encode()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", lambda *a, **k: Response())
    monkeypatch.setattr(MODULE, "CONSTITUENT_ARCHIVE", tmp_path)
    record, failure = MODULE.acquire_current_constituents("2026-11-08T12:00:00+05:30")
    assert failure is None
    assert record["row_count"] == 50
    assert record["unique_symbol_count"] == 50
    assert record["status"] == "CURRENT_COMPOSITION_SNAPSHOT_ARCHIVED_NOT_POINT_IN_TIME_HISTORY"


def test_transient_timeout_is_retried(monkeypatch):
    class Headers(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class Response:
        status = 200
        headers = Headers({"Content-Type": "text/html"})
        def read(self, limit):
            return b"<html>ok</html>"
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    calls = {"count": 0}
    def flaky_urlopen(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("temporary timeout")
        return Response()

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", flaky_urlopen)
    monkeypatch.setattr(MODULE.time, "sleep", lambda seconds: None)
    body, content_type, _ = MODULE.fetch("https://www.nseindia.com/test")
    assert body == b"<html>ok</html>"
    assert content_type == "text/html"
    assert calls["count"] == 3
