from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd


from __future__ import annotations

import hashlib
from pathlib import Path
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

REQUIRED_COLUMNS = {
    "symbol", "ex_date", "action_type", "adjustment_factor", "source",
    "source_url", "source_published_at", "evidence_path", "evidence_sha256",
}


def audit_corporate_action_ledger(path: Path) -> dict:
    """Validate corporate-action evidence without claiming adjusted-price correctness."""
    path = Path(path)
    result = {
        "provided": path.is_file(),
        "valid": False,
        "rows": 0,
        "errors": [],
        "corporate_action_adjustment_verified": False,
        "status": "not_provided",
    }
    if not path.is_file():
        result["errors"].append(f"corporate-action ledger not found: {path}")
        return result
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        result["errors"].append(f"unable to read corporate-action ledger: {type(exc).__name__}")
        result["status"] = "invalid"
        return result
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        result["errors"].append(f"missing columns: {sorted(missing)}")
        result["status"] = "invalid"
        return result

    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["ex_date"] = _india_calendar_dates(frame["ex_date"])
    frame["source_published_at"] = _india_calendar_dates(frame["source_published_at"])
    frame["adjustment_factor"] = pd.to_numeric(frame["adjustment_factor"], errors="coerce")
    if frame["symbol"].eq("").any() or frame["ex_date"].isna().any():
        result["errors"].append("blank symbols or invalid ex_date")
    if frame["action_type"].astype(str).str.strip().eq("").any():
        result["errors"].append("blank action_type")
    if (frame["adjustment_factor"].isna().any()
            or not np.isfinite(frame["adjustment_factor"]).all()
            or (frame["adjustment_factor"] <= 0).any()):
        result["errors"].append("adjustment_factor must be finite and positive")
    if (frame["source_published_at"].dt.normalize() > frame["ex_date"].dt.normalize()).any():
        result["errors"].append("source publication occurs after the corporate action ex_date")
    if frame["source"].astype(str).str.strip().eq("").any():
        result["errors"].append("blank source provenance")
    if frame["source_published_at"].isna().any():
        result["errors"].append("missing or invalid source_published_at")
    urls = frame["source_url"].astype(str).str.strip()
    if any(urlparse(url).scheme != "https" or not urlparse(url).netloc for url in urls):
        result["errors"].append("source_url must be an HTTPS URL")
    if frame["evidence_path"].astype(str).str.strip().eq("").any():
        result["errors"].append("missing evidence_path")
    if frame["evidence_sha256"].astype(str).str.fullmatch(r"[0-9a-fA-F]{64}").eq(False).any():
        result["errors"].append("evidence_sha256 must be a 64-character SHA-256 digest")
    if frame.duplicated(["symbol", "ex_date", "action_type"]).any():
        result["errors"].append("duplicate symbol/ex_date/action_type records")

    for row in frame.itertuples(index=False):
        evidence = Path(str(row.evidence_path))
        if not evidence.is_absolute():
            evidence = path.parent / evidence
        if not evidence.is_file():
            result["errors"].append(f"missing evidence file for {row.symbol}: {row.evidence_path}")
            continue
        digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
        if digest.lower() != str(row.evidence_sha256).lower():
            result["errors"].append(f"evidence checksum mismatch for {row.symbol}: {row.evidence_path}")

    result["rows"] = int(len(frame))
    result["valid"] = not result["errors"] and not frame.empty
    result["status"] = "evidence_valid_unverified_adjustment" if result["valid"] else "invalid"
    result["limitations"] = [
        "Evidence checksum and metadata do not prove that the vendor price series applied the correct adjustment.",
        "Adjusted and unadjusted OHLCV must still be reconciled to the official action terms.",
        "Dividend treatment and total-return consistency require a separate benchmark policy.",
    ]
    return result
