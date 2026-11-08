"""Source-backed NSE equity holiday and special-session calendar.

Coverage is deliberately bounded to explicitly sourced calendar years. Dates
outside a covered period remain unknown; the module never guesses an exchange
holiday calendar or treats an unverified date as a confirmed trading session.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
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


def load_calendar(path: str | Path = DEFAULT_SPECIAL_SESSIONS_PATH) -> dict:
    """Load and validate bounded NSE holiday coverage and special sessions."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("exchange") != "National Stock Exchange of India":
        raise ValueError("calendar has an unexpected exchange")
    if payload.get("segment") != "CAPITAL_MARKET":
        raise ValueError("calendar must target CAPITAL_MARKET")
    coverage = payload.get("calendar_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("calendar coverage metadata is required")
    start = date.fromisoformat(coverage["coverage_start"])
    end = date.fromisoformat(coverage["coverage_end"])
    if start > end:
        raise ValueError("calendar coverage start must not exceed end")
    holidays = coverage.get("holidays")
    if not isinstance(holidays, list):
        raise ValueError("calendar holidays must be a list")
    holiday_map: dict[str, dict] = {}
    for holiday in holidays:
        key = date.fromisoformat(holiday["date"]).isoformat()
        if key in holiday_map:
            raise ValueError(f"duplicate holiday date: {key}")
        holiday_map[key] = holiday
    records = payload.get("special_sessions")
    if not isinstance(records, list):
        raise ValueError("special_sessions must be a list")
    special_map: dict[str, dict] = {}
    for record in records:
        session_date = date.fromisoformat(record["date"])
        if record.get("status") != "OPEN" or record.get("session_type") != "SPECIAL_LIVE_TRADING_SESSION":
            raise ValueError(f"invalid special-session status for {session_date}")
        if not record.get("circular_reference") or not record.get("source_url"):
            raise ValueError(f"special session {session_date} lacks source lineage")
        key = session_date.isoformat()
        if key in special_map:
            raise ValueError(f"duplicate special-session date: {key}")
        special_map[key] = record
    return {
        "payload": payload,
        "coverage_start": start,
        "coverage_end": end,
        "holidays": holiday_map,
        "special_sessions": special_map,
    }


def classify_nse_session_date(
    value: str | date | datetime,
    *,
    special_sessions_path: str | Path = DEFAULT_SPECIAL_SESSIONS_PATH,
) -> dict:
    """Classify a date only when supported by the bounded official calendar."""
    session_date = _nse_date(value)
    calendar = load_calendar(special_sessions_path)
    key = session_date.isoformat()
    scope = "NSE_CAPITAL_MARKET_EQUITIES_2026_OFFICIAL_HOLIDAY_PAGE_AND_SPECIAL_SESSION_CIRCULAR"
    if key in calendar["special_sessions"]:
        return {
            "date": key, "classification": "SPECIAL_TRADING_SESSION",
            "is_trading_session": True, "session": calendar["special_sessions"][key],
            "calendar_scope": scope,
        }
    if not (calendar["coverage_start"] <= session_date <= calendar["coverage_end"]):
        return {
            "date": key, "classification": "OUTSIDE_VERIFIED_CALENDAR_COVERAGE",
            "is_trading_session": None, "session": None,
            "calendar_scope": scope,
        }
    if key in calendar["holidays"]:
        return {
            "date": key, "classification": "EXCHANGE_HOLIDAY",
            "is_trading_session": False, "session": None,
            "holiday": calendar["holidays"][key], "calendar_scope": scope,
        }
    if session_date.weekday() >= 5:
        return {
            "date": key, "classification": "WEEKEND_NO_SESSION",
            "is_trading_session": False, "session": None,
            "calendar_scope": scope,
        }
    return {
        "date": key, "classification": "REGULAR_TRADING_SESSION",
        "is_trading_session": True, "session": None,
        "calendar_scope": scope,
    }


def next_nse_session_date(
    value: str | date | datetime,
    *,
    max_days: int = 14,
    special_sessions_path: str | Path = DEFAULT_SPECIAL_SESSIONS_PATH,
) -> dict:
    """Find the next confirmed session; fail closed at calendar coverage edges."""
    if isinstance(max_days, bool) or not isinstance(max_days, int) or max_days < 1:
        raise ValueError("max_days must be a positive integer")
    start = _nse_date(value)
    for offset in range(1, max_days + 1):
        candidate = start + timedelta(days=offset)
        result = classify_nse_session_date(candidate, special_sessions_path=special_sessions_path)
        if result["classification"] == "OUTSIDE_VERIFIED_CALENDAR_COVERAGE":
            raise RuntimeError(
                f"Cannot confirm next NSE session beyond verified calendar coverage at {candidate.isoformat()}"
            )
        if result["is_trading_session"] is True:
            return {
                "after_date": start.isoformat(),
                "next_session_date": candidate.isoformat(),
                "classification": result["classification"],
                "calendar_scope": result["calendar_scope"],
                "session": result["session"],
            }
    raise RuntimeError(f"No confirmed NSE session found within {max_days} calendar days")
