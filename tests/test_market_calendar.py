from datetime import datetime, timezone
import json

import pytest

from trader.market_calendar import (classify_nse_session_date, load_calendar, load_special_sessions, next_nse_session_date)


def test_november_8_2026_is_recognized_as_sunday_muhurat_session():
    result = classify_nse_session_date("2026-11-08")
    assert result["classification"] == "SPECIAL_TRADING_SESSION"
    assert result["is_trading_session"] is True
    assert result["session"]["circular_reference"] == "NSE/CMTR/76941"
    assert result["session"]["sessions"]["continuous_trading"]["start"] == "14:20"
    assert result["session"]["sessions"]["cash_close_non_cas_securities"] == "15:30"
    assert result["session"]["sessions"]["cash_close_cas_securities"] == "15:15"
    assert result["session"]["settlement_obligation"] is True


def test_timezone_aware_utc_timestamp_is_converted_to_nse_date():
    result = classify_nse_session_date(datetime(2026, 11, 8, 18, 45, tzinfo=timezone.utc))
    assert result["date"] == "2026-11-09"
    assert result["classification"] == "REGULAR_TRADING_SESSION"


def test_unregistered_weekend_is_not_assumed_to_be_open():
    result = classify_nse_session_date("2026-11-07")
    assert result["classification"] == "WEEKEND_NO_SESSION"
    assert result["is_trading_session"] is False


def test_november_10_2026_is_official_exchange_holiday():
    result = classify_nse_session_date("2026-11-10")
    assert result["classification"] == "EXCHANGE_HOLIDAY"
    assert result["is_trading_session"] is False
    assert result["holiday"]["name"] == "Diwali-Balipratipada"


def test_date_outside_verified_calendar_coverage_is_unknown():
    result = classify_nse_session_date("2027-01-04")
    assert result["classification"] == "OUTSIDE_VERIFIED_CALENDAR_COVERAGE"
    assert result["is_trading_session"] is None


def test_next_session_after_muhurat_is_monday_november_9():
    result = next_nse_session_date("2026-11-08")
    assert result["next_session_date"] == "2026-11-09"
    assert result["classification"] == "REGULAR_TRADING_SESSION"


def test_next_session_skips_diwali_balipratipada_holiday():
    result = next_nse_session_date("2026-11-09")
    assert result["next_session_date"] == "2026-11-11"


def test_next_session_fails_closed_when_search_reaches_unverified_year():
    with pytest.raises(RuntimeError, match="verified calendar coverage"):
        next_nse_session_date("2026-12-31")


def test_special_session_register_rejects_duplicate_dates(tmp_path):
    payload = {
        "exchange": "National Stock Exchange of India",
        "segment": "CAPITAL_MARKET",
        "special_sessions": [
            {"date": "2026-11-08", "status": "OPEN",
             "session_type": "SPECIAL_LIVE_TRADING_SESSION",
             "circular_reference": "NSE/CMTR/76941", "source_url": "https://example.invalid/a"},
            {"date": "2026-11-08", "status": "OPEN",
             "session_type": "SPECIAL_LIVE_TRADING_SESSION",
             "circular_reference": "NSE/CMTR/76941", "source_url": "https://example.invalid/b"}
        ]
    }
    path = tmp_path / "sessions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate special-session date"):
        load_special_sessions(path)


def test_missing_source_lineage_is_rejected(tmp_path):
    payload = {
        "exchange": "National Stock Exchange of India",
        "segment": "CAPITAL_MARKET",
        "special_sessions": [{
            "date": "2026-11-08", "status": "OPEN",
            "session_type": "SPECIAL_LIVE_TRADING_SESSION",
            "circular_reference": "", "source_url": ""
        }]
    }
    path = tmp_path / "sessions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="lacks source lineage"):
        load_special_sessions(path)
