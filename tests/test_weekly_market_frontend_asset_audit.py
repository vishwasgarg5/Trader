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
    response = MODULE.open_with_retry(object(), timeout=MODULE.ASSET_TIMEOUT)
    assert isinstance(response, Response)
    assert calls == [MODULE.ASSET_TIMEOUT, MODULE.ASSET_TIMEOUT]
