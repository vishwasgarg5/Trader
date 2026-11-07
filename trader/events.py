from __future__ import annotations

"""Point-in-time corporate-action event ingestion.

Only announcement-dated exchange records are eligible for model features.
Yahoo Finance actions are deliberately treated as a reconciliation source:
they do not contain a reliable historical announcement timestamp.
"""

import argparse
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

EVENT_COLUMNS = [
    "symbol", "event_type", "announce_date", "ex_date", "value",
    "source_url", "source_hash",
]

_ALIASES = {
    "symbol": ("symbol", "security", "ticker"),
    "event_type": ("event_type", "purpose", "subject", "action_type"),
    "announce_date": ("announce_date", "announcement_date", "broadcast_date", "dissemination_date"),
    "ex_date": ("ex_date", "ex-date", "exdate"),
    "value": ("value", "dividend", "dividend_amount", "ratio", "face_value"),
}


def _column_map(columns: list[str]) -> dict[str, str]:
    normalized = {str(column).strip().lower().replace(" ", "_"): str(column) for column in columns}
    result: dict[str, str] = {}
    for target, aliases in _ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                result[target] = normalized[alias]
                break
    missing = sorted(set(_ALIASES).difference(result))
    if missing:
        raise ValueError("Source CSV is missing required fields: " + ", ".join(missing))
    return result


def normalize_nse_actions(source_path: Path, source_url: str) -> pd.DataFrame:
    """Parse an archived NSE corporate-actions CSV into a point-in-time event table.

    announce_date is mandatory. The loader never substitutes ex_date, file
    download time, or a later filing timestamp for a missing announcement date.
    """
    source_path = Path(source_path)
    if urlparse(source_url).scheme != "https" or not urlparse(source_url).netloc:
        raise ValueError("source_url must be an HTTPS URL")
    raw_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(raw_bytes).hexdigest()
    frame = pd.read_csv(source_path, dtype=str)
    if frame.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    columns = _column_map(list(frame.columns))
    events = pd.DataFrame({name: frame[column] for name, column in columns.items()})
    events["symbol"] = events["symbol"].astype(str).str.strip().str.upper()
    events["event_type"] = events["event_type"].astype(str).str.strip().str.lower()
    for name in ("announce_date", "ex_date"):
        events[name] = pd.to_datetime(events[name], errors="coerce", dayfirst=True).dt.normalize()
    events["value"] = pd.to_numeric(
        events["value"].astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False),
        errors="coerce",
    )
    if events["symbol"].eq("").any() or events["symbol"].isna().any():
        raise ValueError("blank symbol in source CSV")
    if events["event_type"].eq("").any() or events["event_type"].isna().any():
        raise ValueError("blank event_type in source CSV")
    if events[["announce_date", "ex_date"]].isna().any().any():
        raise ValueError("announcement date and ex-date are both required; dates are never inferred")
    if (events["announce_date"] > events["ex_date"]).any():
        raise ValueError("announcement date occurs after ex-date; refusing look-ahead event")
    events["source_url"] = source_url
    events["source_hash"] = source_hash
    events = events[EVENT_COLUMNS]
    events["announce_date"] = events["announce_date"].dt.strftime("%Y-%m-%d")
    events["ex_date"] = events["ex_date"].dt.strftime("%Y-%m-%d")
    return events


def merge_events(events: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """Append new events idempotently, preserving the exact event-table schema."""
    output_path = Path(output_path)
    if list(events.columns) != EVENT_COLUMNS:
        raise ValueError("events dataframe does not match EVENT_COLUMNS")
    if output_path.exists():
        existing = pd.read_csv(output_path, dtype=str)
        if list(existing.columns) != EVENT_COLUMNS:
            raise ValueError("existing events table has an incompatible schema")
        events = pd.concat([existing, events], ignore_index=True)
    events = events.drop_duplicates(
        subset=["symbol", "event_type", "announce_date", "ex_date", "source_hash"],
        keep="last",
    ).sort_values(["announce_date", "symbol", "event_type"], kind="stable")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(output_path, index=False)
    return events


def yfinance_action_crosscheck(actions: pd.DataFrame) -> pd.DataFrame:
    """Return Yahoo action dates/values for reconciliation only, never feature use."""
    if actions is None or actions.empty:
        return pd.DataFrame(columns=["action_date", "dividends", "stock_splits"])
    result = actions.copy()
    result.index = pd.to_datetime(result.index, errors="coerce").normalize()
    for column in ("Dividends", "Stock Splits"):
        if column not in result:
            result[column] = 0.0
    result = result.rename(columns={
        "Dividends": "dividends", "Stock Splits": "stock_splits",
    })
    result.index.name = "action_date"
    return result[["dividends", "stock_splits"]].reset_index()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest archived NSE corporate actions into the PIT events table")
    parser.add_argument("source_csv", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/reference/events.csv"))
    args = parser.parse_args()
    events = normalize_nse_actions(args.source_csv, args.source_url)
    merged = merge_events(events, args.output)
    print(f"Ingested {len(events)} source rows; events table now contains {len(merged)} unique rows")


if __name__ == "__main__":
    main()
