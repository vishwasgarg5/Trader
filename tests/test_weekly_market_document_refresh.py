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
