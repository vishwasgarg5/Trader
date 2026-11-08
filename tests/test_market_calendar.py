from datetime import datetime, timezone
import json

import pytest

from trader.market_calendar import classify_nse_session_date, load_special_sessions


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
    assert result["classification"] == "WEEKDAY_REQUIRES_OFFICIAL_HOLIDAY_CALENDAR"


def test_unregistered_weekend_is_not_assumed_to_be_open():
    result = classify_nse_session_date("2026-11-07")
    assert result["classification"] == "WEEKEND_NO_SESSION_CONFIRMED"
    assert result["is_trading_session"] is None


def test_weekday_is_not_assumed_open_without_full_holiday_calendar():
    result = classify_nse_session_date("2026-11-10")
    assert result["classification"] == "WEEKDAY_REQUIRES_OFFICIAL_HOLIDAY_CALENDAR"
    assert result["is_trading_session"] is None


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
