from scripts.crosscheck_nippon_nifty50_with_nse_bhavcopy import map_isins_to_symbols


def test_map_isins_to_symbols_uses_eq_series_and_reports_missing():
    holdings = [
        {"isin": "INE040A01034", "security_name": "HDFC Bank"},
        {"isin": "INE090A01021", "security_name": "ICICI Bank"},
    ]
    bhav = [
        {"isin": "INE040A01034", "symbol": "HDFCBANK", "series": "EQ"},
        {"isin": "INE090A01021", "symbol": "ICICIBANK", "series": "BE"},
    ]
    mapped, missing = map_isins_to_symbols(holdings, bhav)
    assert [x["symbol"] for x in mapped] == ["HDFCBANK"]
    assert missing == ["INE090A01021"]


def test_map_isins_to_symbols_rejects_conflicting_isin_identity():
    holdings = [{"isin": "INE040A01034", "security_name": "HDFC Bank"}]
    bhav = [
        {"isin": "INE040A01034", "symbol": "HDFCBANK", "series": "EQ"},
        {"isin": "INE040A01034", "symbol": "OTHER", "series": "EQ"},
    ]
    try:
        map_isins_to_symbols(holdings, bhav)
    except ValueError as exc:
        assert "multiple EQ symbols" in str(exc)
    else:
        raise AssertionError("conflicting ISIN identity must fail closed")
