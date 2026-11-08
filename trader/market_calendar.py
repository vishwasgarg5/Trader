"""Source-backed NSE special-session overrides.

This deliberately is not a complete exchange holiday calendar. Unknown weekdays
are not asserted to be open, and unknown weekend dates are not asserted to be
special sessions.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPECIAL_SESSIONS_PATH = ROOT / "config" / "nse_special_sessions.json"
NSE_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _nse_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        stamp = value
        if stamp.tzinfo is not None:
            stamp = stamp.astimezone(NSE_TIMEZONE)
        return stamp.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise TypeError("NSE session date must be a date, datetime, or ISO date string")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(NSE_TIMEZONE)
    return stamp.date()


def load_special_sessions(path: str | Path = DEFAULT_SPECIAL_SESSIONS_PATH) -> dict[str, dict]:
    """Load and validate the explicit date-keyed special-session register."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("exchange") != "National Stock Exchange of India":
        raise ValueError("special-session register has an unexpected exchange")
    if payload.get("segment") != "CAPITAL_MARKET":
        raise ValueError("special-session register must target CAPITAL_MARKET")
    records = payload.get("special_sessions")
    if not isinstance(records, list):
        raise ValueError("special_sessions must be a list")
    result: dict[str, dict] = {}
    for record in records:
        session_date = date.fromisoformat(record["date"])
        if record.get("status") != "OPEN" or record.get("session_type") != "SPECIAL_LIVE_TRADING_SESSION":
            raise ValueError(f"invalid special-session status for {session_date}")
        if not record.get("circular_reference") or not record.get("source_url"):
            raise ValueError(f"special session {session_date} lacks source lineage")
        key = session_date.isoformat()
        if key in result:
            raise ValueError(f"duplicate special-session date: {key}")
        result[key] = record
    return result


def classify_nse_session_date(
    value: str | date | datetime,
    *,
    special_sessions_path: str | Path = DEFAULT_SPECIAL_SESSIONS_PATH,
) -> dict:
    """Classify only what this partial register can prove; never infer holidays."""
    session_date = _nse_date(value)
    special_sessions = load_special_sessions(special_sessions_path)
    key = session_date.isoformat()
    if key in special_sessions:
        return {
            "date": key,
            "classification": "SPECIAL_TRADING_SESSION",
            "is_trading_session": True,
            "session": special_sessions[key],
            "calendar_scope": "DATE_SPECIFIC_SPECIAL_SESSION_REGISTER_NOT_COMPLETE_HOLIDAY_CALENDAR",
        }
    if session_date.weekday() >= 5:
        return {
            "date": key,
            "classification": "WEEKEND_NO_SESSION_CONFIRMED",
            "is_trading_session": None,
            "session": None,
            "calendar_scope": "DATE_SPECIFIC_SPECIAL_SESSION_REGISTER_NOT_COMPLETE_HOLIDAY_CALENDAR",
        }
    return {
        "date": key,
        "classification": "WEEKDAY_REQUIRES_OFFICIAL_HOLIDAY_CALENDAR",
        "is_trading_session": None,
        "session": None,
        "calendar_scope": "DATE_SPECIFIC_SPECIAL_SESSION_REGISTER_NOT_COMPLETE_HOLIDAY_CALENDAR",
    }
