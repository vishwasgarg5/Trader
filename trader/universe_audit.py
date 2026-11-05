from __future__ import annotations

from pathlib import Path
import hashlib
from urllib.parse import urlparse

import pandas as pd


MEMBERSHIP_COLUMNS = {
    "symbol", "valid_from", "valid_to", "source", "source_url",
    "source_published_at", "evidence_path", "evidence_sha256",
}


def audit_universe(
    prices: dict[str, pd.DataFrame],
    configured_symbols: list[str],
    membership_path: Path,
) -> dict:
    """Audit price-panel integrity and explicitly grade constituent-history evidence.

    A configured ticker list is a static research snapshot, never point-in-time
    membership evidence. Membership is considered auditable only when a dated,
    sourced membership file is supplied and passes schema/date checks.
    """
    benchmark = prices.get("^NSEI")
    benchmark_dates = (
        pd.DatetimeIndex(pd.to_datetime(benchmark.index)).tz_localize(None).normalize()
        if benchmark is not None else pd.DatetimeIndex([])
    )
    symbols = sorted({str(s).strip().upper() for s in configured_symbols})
    per_symbol = {}
    for symbol in symbols:
        frame = prices.get(symbol)
        if frame is None or frame.empty:
            per_symbol[symbol] = {"present": False, "rows": 0, "duplicate_dates": 0,
                                  "invalid_ohlc_rows": None, "zero_volume_rows": None,
                                  "missing_benchmark_sessions": None, "stale_benchmark_sessions": None, "last_date": None}
            continue
        dates = pd.DatetimeIndex(pd.to_datetime(frame.index)).tz_localize(None).normalize()
        duplicate_count = int(dates.duplicated().sum())
        required = {"open", "high", "low", "close", "volume"}
        invalid = None
        zero_volume = None
        if required.issubset(frame.columns):
            bars = frame[list(required)].apply(pd.to_numeric, errors="coerce")
            invalid_mask = (
                bars[["open", "high", "low", "close"]].isna().any(axis=1)
                | (bars[["open", "high", "low", "close"]] <= 0).any(axis=1)
                | (bars["high"] < bars[["open", "low", "close"]].max(axis=1))
                | (bars["low"] > bars[["open", "high", "close"]].min(axis=1))
                | bars["volume"].isna() | (bars["volume"] < 0)
            )
            invalid = int(invalid_mask.sum())
            zero_volume = int((bars["volume"] == 0).sum())
        expected = benchmark_dates[(benchmark_dates >= dates.min()) & (benchmark_dates <= dates.max())] if len(benchmark_dates) else pd.DatetimeIndex([])
        missing_sessions = int(len(expected.difference(dates)))
        stale_sessions = int((benchmark_dates > dates.max()).sum()) if len(benchmark_dates) else 0
        per_symbol[symbol] = {
            "present": True, "rows": int(len(frame)), "duplicate_dates": duplicate_count,
            "invalid_ohlc_rows": invalid, "zero_volume_rows": zero_volume,
            "missing_benchmark_sessions": missing_sessions,
            "stale_benchmark_sessions": stale_sessions,
            "last_date": str(dates.max().date()),
        }

    membership = {"provided": membership_path.exists(), "valid": False,
                  "point_in_time_verified": False, "rows": 0, "errors": []}
    if membership_path.exists():
        try:
            history = pd.read_csv(membership_path)
            missing = MEMBERSHIP_COLUMNS.difference(history.columns)
            if missing:
                membership["errors"].append(f"missing columns: {sorted(missing)}")
            else:
                history["symbol"] = history["symbol"].astype(str).str.strip().str.upper()
                history["valid_from"] = pd.to_datetime(history["valid_from"], errors="coerce")
                history["valid_to"] = pd.to_datetime(history["valid_to"], errors="coerce")
                history["source_published_at"] = pd.to_datetime(history["source_published_at"], errors="coerce")
                if history["symbol"].eq("").any() or history["valid_from"].isna().any():
                    membership["errors"].append("blank symbols or invalid valid_from dates")
                if (history["valid_to"].notna() & (history["valid_to"] < history["valid_from"])).any():
                    membership["errors"].append("valid_to precedes valid_from")
                if history["source"].astype(str).str.strip().eq("").any():
                    membership["errors"].append("blank source provenance")
                if history["source_published_at"].isna().any():
                    membership["errors"].append("missing source_published_at timestamps")
                elif (history["source_published_at"].dt.normalize()
                      > history["valid_from"].dt.normalize()).any():
                    membership["errors"].append("membership source was published after valid_from")
                urls = history["source_url"].astype(str).str.strip()
                if any(urlparse(url).scheme != "https" or not urlparse(url).netloc for url in urls):
                    membership["errors"].append("source_url must be an HTTPS URL")
                if history["evidence_path"].astype(str).str.strip().eq("").any():
                    membership["errors"].append("missing evidence_path")
                if history["evidence_sha256"].astype(str).str.fullmatch(r"[0-9a-fA-F]{64}").eq(False).any():
                    membership["errors"].append("evidence_sha256 must be a 64-character SHA-256 digest")
                if history.duplicated(["symbol", "valid_from"]).any():
                    membership["errors"].append("duplicate symbol/valid_from records")
                for symbol, group in history.sort_values(["symbol", "valid_from"]).groupby("symbol"):
                    previous_end = None
                    for row in group.itertuples(index=False):
                        start = row.valid_from
                        end = row.valid_to
                        if previous_end is not None and (pd.isna(previous_end) or start <= previous_end):
                            membership["errors"].append(f"overlapping membership intervals for {symbol}")
                            break
                        previous_end = end
                for row in history.itertuples(index=False):
                    evidence = Path(str(row.evidence_path))
                    if not evidence.is_absolute():
                        evidence = membership_path.parent / evidence
                    if not evidence.is_file():
                        membership["errors"].append(f"missing evidence file for {row.symbol}: {row.evidence_path}")
                        continue
                    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
                    if digest.lower() != str(row.evidence_sha256).lower():
                        membership["errors"].append(f"evidence checksum mismatch for {row.symbol}: {row.evidence_path}")
                membership["rows"] = int(len(history))
                membership["valid"] = not membership["errors"] and not history.empty
                # Even schema-valid user-supplied data is not independently
                # authenticated here; keep the strong PIT claim false.
        except (OSError, pd.errors.ParserError, UnicodeError) as exc:
            membership["errors"].append(f"unable to read membership history: {type(exc).__name__}")

    missing_symbols = [s for s, row in per_symbol.items() if not row["present"]]
    integrity_issues = {
        s: row for s, row in per_symbol.items()
        if row["present"] and (
            row["duplicate_dates"] or row["invalid_ohlc_rows"] or row["missing_benchmark_sessions"] or row["stale_benchmark_sessions"]
        )
    }
    return {
        "configured_symbol_count": len(symbols),
        "price_symbol_count": sum(row["present"] for row in per_symbol.values()),
        "missing_symbols": missing_symbols,
        "price_integrity_issues": integrity_issues,
        "per_symbol": per_symbol,
        "membership_history": membership,
        "point_in_time_universe_verified": False,
        "corporate_action_adjustment_verified": False,
        "limitations": [
            "The configured universe is a static ticker snapshot, not historical index membership.",
            "Yahoo Finance adjusted-price semantics and corporate-action completeness are not independently verified.",
            "Missing benchmark sessions are a diagnostic; holidays, suspensions and source gaps require manual adjudication.",
            "Delisted securities and historical constituents absent from the configured list cannot be recovered from this panel.",
            "Membership file provenance is not independently authenticated by this audit.",
        ],
    }
