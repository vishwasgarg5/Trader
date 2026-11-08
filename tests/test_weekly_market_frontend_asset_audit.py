import importlib.util
import pathlib

SPEC = importlib.util.spec_from_file_location(
    "weekly_market_frontend_asset_audit",
    pathlib.Path("scripts/weekly_market_frontend_asset_audit.py"),
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_only_observed_official_nse_filing_scripts_are_selected():
    page = """
    <script src="/dist/js/components/corporate-filing/csps/announcements-csp.js"></script>
    <script src="https://evil.example/steal.js"></script>
    <script src="http://www.nseindia.com/insecure.js"></script>
    <script src="/assets/js/site.js"></script>
    """
    urls = MODULE.observed_script_urls(page, "https://www.nseindia.com/companies-listing/corporate-filings-announcements")
    assert urls == ["https://www.nseindia.com/dist/js/components/corporate-filing/csps/announcements-csp.js"]


def test_candidate_routes_are_review_only_and_not_general_navigation_links():
    source = """
    const a = "/api/corporate-announcements";
    const b = "/api/corporateActions";
    const c = "/resources/exchange-communication-holidays";
    const d = "/companies-listing/corporate-filings-announcements";
    """
    routes = MODULE.candidate_routes(source)
    assert "/api/corporate-announcements" in routes
    assert "/api/corporateActions" in routes
    assert "/resources/exchange-communication-holidays" not in routes
    assert "/companies-listing/corporate-filings-announcements" not in routes


def test_route_discovery_does_not_authorize_execution():
    assert "NOT_CALLED" in pathlib.Path("scripts/weekly_market_frontend_asset_audit.py").read_text()
    assert "candidate_routes_for_manual_review" in pathlib.Path("scripts/weekly_market_frontend_asset_audit.py").read_text()


def test_transient_frontend_asset_timeout_is_retried(monkeypatch):
    calls = []

    class Response:
        url = "https://www.nseindia.com/dist/js/components/corporate-filing/test.js"
        headers = {"Content-Type": "application/javascript"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"const ok = true;"

    def flaky_get(url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise TimeoutError("temporary read timeout")
        return Response()

    monkeypatch.setattr(MODULE.curl_requests, "get", flaky_get)
    monkeypatch.setattr(MODULE.time, "sleep", lambda _seconds: None)
    body, content_type, final_url = MODULE.fetch_asset(
        "https://www.nseindia.com/dist/js/components/corporate-filing/test.js"
    )
    assert body == b"const ok = true;"
    assert "javascript" in content_type
    assert final_url.startswith("https://www.nseindia.com/")
    assert len(calls) == 2
    assert calls[0]["impersonate"] == "chrome"
    assert calls[0]["timeout"] == (20, MODULE.ASSET_TIMEOUT)


def test_asset_fetch_rejects_redirect_outside_official_hosts(monkeypatch):
    class Response:
        url = "https://evil.example/asset.js"
        headers = {"Content-Type": "application/javascript"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"malicious"

    monkeypatch.setattr(MODULE.curl_requests, "get", lambda *args, **kwargs: Response())
    try:
        MODULE.fetch_asset("https://www.nseindia.com/dist/js/components/corporate-filing/test.js")
    except ValueError as exc:
        assert "redirect left official NSE host allowlist" in str(exc)
    else:
        raise AssertionError("off-host redirect must be rejected")


def test_asset_audit_uses_bounded_concurrency_to_fit_workflow_timeout():
    assert MODULE.MAX_WORKERS == 4
    source = pathlib.Path("scripts/weekly_market_frontend_asset_audit.py").read_text()
    assert "ThreadPoolExecutor(max_workers=MAX_WORKERS)" in source
    assert "pool.map" in source
