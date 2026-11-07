from __future__ import annotations

from pathlib import Path
import hashlib
from urllib.parse import urlparse

import numpy as np
import pandas as pd


def _india_calendar_dates(values: pd.Series) -> pd.Series:
    """Parse timestamps as NSE calendar dates without shifting naive local values."""
    def to_india_date(value):
        try:
            stamp = pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError):
            return pd.NaT
        if pd.isna(stamp):
            return pd.NaT
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize("Asia/Kolkata")
        else:
            stamp = stamp.tz_convert("Asia/Kolkata")
        return stamp.tz_localize(None).normalize()

    return pd.Series(
        values.map(to_india_date),
        index=values.index,
        dtype="datetime64[ns]",
    )


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
        pd.DatetimeIndex(_india_calendar_dates(pd.Series(benchmark.index)).dropna())
        if benchmark is not None else pd.DatetimeIndex([])
    )
    symbols = sorted({str(s).strip().upper() for s in configured_symbols})
    per_symbol = {}
    for symbol in symbols:
        frame = prices.get(symbol)
        if frame is None or frame.empty:
            per_symbol[symbol] = {"present": False, "rows": 0, "duplicate_dates": 0,
                                  "invalid_ohlc_rows": None, "zero_volume_rows": None,
                                  "missing_ohlcv_columns": ["open", "high", "low", "close", "volume"],
                                  "missing_benchmark_sessions": None, "stale_benchmark_sessions": None, "last_date": None}
            continue
        dates = pd.DatetimeIndex(_india_calendar_dates(pd.Series(frame.index)).dropna())
        duplicate_count = int(dates.duplicated().sum())
        invalid_date_rows = int(len(frame) - len(dates))
        required = {"open", "high", "low", "close", "volume"}
        missing_columns = sorted(required.difference(frame.columns))
        invalid = None
        zero_volume = None
        if required.issubset(frame.columns):
            bars = frame[list(required)].apply(pd.to_numeric, errors="coerce")
            invalid_mask = (
                bars[["open", "high", "low", "close"]].isna().any(axis=1)
                | ~np.isfinite(bars).all(axis=1)
                | (bars[["open", "high", "low", "close"]] <= 0).any(axis=1)
                | (bars["high"] < bars[["open", "low", "close"]].max(axis=1))
                | (bars["low"] > bars[["open", "high", "close"]].min(axis=1))
                | bars["volume"].isna() | (bars["volume"] < 0)
            )
            invalid = int(invalid_mask.sum())
            zero_volume = int((bars["volume"] == 0).sum())
        expected = (
            benchmark_dates[(benchmark_dates >= dates.min()) & (benchmark_dates <= dates.max())]
            if len(benchmark_dates) and len(dates) else pd.DatetimeIndex([])
        )
        missing_sessions = int(len(expected.difference(dates)))
        stale_sessions = int((benchmark_dates > dates.max()).sum()) if len(benchmark_dates) and len(dates) else 0
        per_symbol[symbol] = {
            "present": True, "rows": int(len(frame)), "duplicate_dates": duplicate_count,
            "invalid_date_rows": invalid_date_rows,
            "invalid_ohlc_rows": invalid, "zero_volume_rows": zero_volume,
            "missing_ohlcv_columns": missing_columns,
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
                history["valid_from"] = _india_calendar_dates(history["valid_from"])
                history["valid_to"] = _india_calendar_dates(history["valid_to"])
                history["source_published_at"] = _india_calendar_dates(history["source_published_at"])
                membership_symbols = set(history["symbol"].dropna())
                missing_membership = sorted(set(symbols) - membership_symbols)
                # Historical index members are expected to differ from today's
                # configured ticker snapshot. Former, delisted and replaced symbols
                # must remain in the point-in-time ledger to avoid survivorship bias.
                if missing_membership:
                    membership["errors"].append(
                        f"configured symbols missing from membership evidence: {missing_membership}"
                    )
                if history["symbol"].eq("").any() or history["valid_from"].isna().any():
                    membership["errors"].append("blank symbols or invalid valid_from dates")
                if (history["valid_to"].notna() & (history["valid_to"] <= history["valid_from"])).any():
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
                        if previous_end is not None and (pd.isna(previous_end) or start < previous_end):
                            membership["errors"].append(f"overlapping membership intervals for {symbol}")
                            break
                        previous_end = end
                for row in history.itertuples(index=False):
                    relative_evidence = Path(str(row.evidence_path))
                    if relative_evidence.is_absolute() or ".." in relative_evidence.parts:
                        membership["errors"].append(
                            f"evidence_path escapes membership directory for {row.symbol}: {row.evidence_path}"
                        )
                        continue
                    evidence_root = membership_path.parent.resolve()
                    evidence = (evidence_root / relative_evidence).resolve()
                    try:
                        evidence.relative_to(evidence_root)
                    except ValueError:
                        membership["errors"].append(
                            f"evidence_path escapes membership directory for {row.symbol}: {row.evidence_path}"
                        )
                        continue
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
            row["duplicate_dates"] or row.get("invalid_date_rows", 0) or row["invalid_ohlc_rows"] or row["missing_ohlcv_columns"] or row["missing_benchmark_sessions"] or row["stale_benchmark_sessions"]
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
            "Membership intervals use half-open [valid_from, valid_to) semantics.",
        ],
    }



def apply_point_in_time_membership(
    frame: pd.DataFrame, membership_path: Path, universe_audit: dict
) -> tuple[pd.DataFrame, dict]:
    """Apply only evidence-audited membership intervals; otherwise keep static research explicit."""
    if not membership_path.exists():
        return frame.copy(), {
            "applied": False,
            "mode": "static_configured_unverified",
            "rows_before": int(len(frame)),
            "rows_after": int(len(frame)),
            "rows_removed": 0,
            "reason": "No official dated membership history file is present.",
            "point_in_time_verified": False,
        }
    membership_status = universe_audit.get("membership_history", {})
    if not membership_status.get("valid"):
        raise ValueError(
            "Refusing to apply an invalid membership history: "
            + "; ".join(membership_status.get("errors", []))
        )

    history = pd.read_csv(membership_path)
    history["symbol"] = history["symbol"].astype(str).str.strip().str.upper()
    history["valid_from"] = _india_calendar_dates(history["valid_from"])
    history["valid_to"] = _india_calendar_dates(history["valid_to"])
    left = frame.reset_index(names="date").copy()
    left["date"] = _india_calendar_dates(left["date"])
    left["symbol"] = left["symbol"].astype(str).str.strip().str.upper()
    merged = left.merge(
        history[["symbol", "valid_from", "valid_to"]],
        on="symbol", how="left", validate="many_to_many",
    )
    active = (
        merged["valid_from"].notna()
        & (merged["date"] >= merged["valid_from"])
        & (merged["valid_to"].isna() | (merged["date"] < merged["valid_to"]))
    )
    filtered = merged.loc[active].drop(columns=["valid_from", "valid_to"])
    if filtered.empty:
        raise ValueError("Membership history excludes every experiment row; refusing empty research run.")
    filtered = filtered.set_index("date").sort_index()
    return filtered, {
        "applied": True,
        "mode": "evidence_audited_membership_intervals",
        "rows_before": int(len(frame)),
        "rows_after": int(len(filtered)),
        "rows_removed": int(len(frame) - len(filtered)),
        "point_in_time_verified": False,
        "reason": "Evidence files and metadata passed structural checks, but source authenticity still requires independent review.",
    }
