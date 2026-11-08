import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "market_source_fetcher", Path("trader/market_source_fetcher.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_official_url_allowlist_requires_https_and_exact_host():
    allowed = {"nseindia.com", "www.nseindia.com"}
    MODULE.validate_official_url("https://www.nseindia.com/a.pdf", allowed)
    for url in ("http://www.nseindia.com/a.pdf", "https://evil.example/a.pdf",
                "https://www.nseindia.com.evil.example/a.pdf"):
        try:
            MODULE.validate_official_url(url, allowed)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe URL accepted: {url}")


def test_pdf_validation_requires_signature_and_eof():
    # Validation is performed after a complete fetch; exercise the contract via a stubbed session.
    class Response:
        url = "https://www.nseindia.com/a.pdf"
        status_code = 200
        headers = {"Content-Type": "application/pdf", "Content-Length": "19"}

        def iter_content(self, chunk_size):
            yield b"%PDF-1.7\\nbody\\n%%EOF"

    class Session:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, *args, **kwargs): return Response()

    original = MODULE.curl_requests.Session
    original_egress = MODULE.egress_identity
    MODULE.curl_requests.Session = Session
    MODULE.egress_identity = lambda: {"ip": "198.51.100.1"}
    try:
        body, meta = MODULE.fetch_bytes(
            "https://www.nseindia.com/a.pdf", allowed_hosts={"www.nseindia.com"},
            expected_content_type=("pdf",), pdf=True, attempts=1
        )
        assert body.startswith(b"%PDF")
        assert meta["status"] == "FETCHED_AND_VALIDATED"
    finally:
        MODULE.curl_requests.Session = original
        MODULE.egress_identity = original_egress


def test_fetch_failure_exposes_auditable_metadata(monkeypatch):
    class Session:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, *args, **kwargs): raise TimeoutError("timed out")

    monkeypatch.setattr(MODULE.curl_requests, "Session", Session)
    monkeypatch.setattr(MODULE, "egress_identity", lambda: {"ip": "203.0.113.1"})
    monkeypatch.setattr(MODULE.time, "sleep", lambda *_: None)
    try:
        MODULE.fetch_bytes("https://www.nseindia.com/a.pdf",
                           allowed_hosts={"www.nseindia.com"}, attempts=1)
    except MODULE.FetchError as exc:
        assert exc.metadata["status"] == "FETCH_FAILED"
        assert len(exc.metadata["attempts"]) == 2
    else:
        raise AssertionError("failed source must not return a success result")
