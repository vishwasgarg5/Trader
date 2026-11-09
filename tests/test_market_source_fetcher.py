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
            yield b"%PDF-1.7\nbody\n%%EOF"

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



def test_http2_failure_falls_back_to_http11(monkeypatch):
    requested_versions = []

    class Response:
        url = "https://www.nseindia.com/a.pdf"
        status_code = 200
        headers = {"Content-Type": "application/pdf", "Content-Length": "19"}

        def iter_content(self, chunk_size):
            yield b"%PDF-1.7\nbody\n%%EOF"

    class Session:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, *args, **kwargs):
            version = kwargs.get("http_version")
            requested_versions.append(version)
            if version == MODULE.CurlHttpVersion.V2_0:
                raise ConnectionError("simulated HTTP/2 connection failure")
            return Response()

    monkeypatch.setattr(MODULE.curl_requests, "Session", Session)
    monkeypatch.setattr(MODULE, "egress_identity", lambda: {"ip": "203.0.113.1"})
    body, metadata = MODULE.fetch_bytes(
        "https://www.nseindia.com/a.pdf",
        allowed_hosts={"www.nseindia.com"},
        pdf=True,
        attempts=1,
    )

    assert body.startswith(b"%PDF")
    assert requested_versions == [
        MODULE.CurlHttpVersion.V2_0,
        MODULE.CurlHttpVersion.V1_1,
    ]
    assert [attempt["protocol"] for attempt in metadata["attempts"]] == [
        "http2",
        "http1.1",
    ]



def test_redirect_chain_is_validated_before_each_network_request():
    requested = []

    class Response:
        def __init__(self, url, status, headers=None):
            self.url = url
            self.status_code = status
            self.headers = headers or {}

    class Session:
        def get(self, url, **kwargs):
            requested.append((url, kwargs.get("allow_redirects")))
            if url == "https://www.nseindia.com/start":
                return Response(url, 302, {"Location": "https://evil.example/collect"})
            raise AssertionError("disallowed redirect target must not be requested")

    try:
        MODULE._get_allowlisted(
            Session(),
            "https://www.nseindia.com/start",
            {"www.nseindia.com"},
        )
    except ValueError as exc:
        assert "allowlisted official host" in str(exc)
    else:
        raise AssertionError("disallowed intermediate redirect was accepted")

    assert requested == [("https://www.nseindia.com/start", False)]


def test_redirect_chain_records_only_allowlisted_hops():
    requested = []

    class Response:
        def __init__(self, url, status, headers=None):
            self.url = url
            self.status_code = status
            self.headers = headers or {}

    class Session:
        def get(self, url, **kwargs):
            requested.append(url)
            if url == "https://www.nseindia.com/start":
                return Response(url, 302, {"Location": "/archive/final.csv"})
            return Response(url, 200)

    response, chain = MODULE._get_allowlisted(
        Session(),
        "https://www.nseindia.com/start",
        {"www.nseindia.com"},
    )

    assert response.url == "https://www.nseindia.com/archive/final.csv"
    assert chain == [
        "https://www.nseindia.com/start",
        "https://www.nseindia.com/archive/final.csv",
    ]
    assert requested == chain
