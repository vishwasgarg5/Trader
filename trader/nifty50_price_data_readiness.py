"""Fail-closed readiness audit for Nifty 50 pilot OHLCV and TRI data."""
from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from trader.corporate_actions import audit_corporate_action_ledger
from trader.nifty50_pit_readiness import audit_pit_readiness
from trader.security_aliases import audit_security_aliases, is_valid_isin

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data" / "reference"
OHLCV_COLUMNS = {
    "security_id", "symbol", "session_date", "open", "high", "low", "close",
    "volume", "adjusted_close", "source_url", "source_published_at",
    "evidence_path", "evidence_sha256", "verification_status", "reviewer", "reviewed_at",
}
TRI_COLUMNS = {
    "session_date", "tri_close", "source_url", "source_published_at",
    "evidence_path", "evidence_sha256", "verification_status", "reviewer", "reviewed_at",
}


def _read(path: Path, required: set[str]) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            if not columns:
                return [], [f"{path.name}: missing CSV header"]
            missing = sorted(required - columns)
            if missing:
                errors.append(f"{path.name}: missing columns {missing}")
            return list(reader), errors
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], [f"{path.name}: cannot read ({type(exc).__name__})"]


def _audit_rows(
    path: Path,
    rows: list[dict[str, str]],
    *,
    tri: bool,
    evidence_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    verified_evidence: dict[Path, str | None] = {}
    resolved_evidence_root = evidence_root.resolve() if evidence_root is not None else None
    for line, row in enumerate(rows, start=2):
        label = f"{path.name}:{line}"
        symbol = "NIFTY50_TRI" if tri else row.get("security_id", "").strip()
        try:
            session = date.fromisoformat(row.get("session_date", "").strip())
        except ValueError:
            errors.append(f"{label}: invalid session_date")
            continue
        key = (symbol, session.isoformat())
        if key in seen:
            errors.append(f"{label}: duplicate security/session date")
        seen.add(key)

        price_fields = ("tri_close",) if tri else ("open", "high", "low", "close", "adjusted_close", "volume")
        values: dict[str, float] = {}
        for field in price_fields:
            try:
                value = float(row.get(field, ""))
            except (TypeError, ValueError):
                errors.append(f"{label}: missing or invalid {field}")
                continue
            if not math.isfinite(value) or value <= 0:
                errors.append(f"{label}: {field} must be finite and positive")
            values[field] = value
        if not tri and all(field in values for field in ("open", "high", "low", "close")):
            if values["high"] < max(values["open"], values["low"], values["close"]):
                errors.append(f"{label}: high is below another OHLC value")
            if values["low"] > min(values["open"], values["high"], values["close"]):
                errors.append(f"{label}: low is above another OHLC value")
        if not tri and "volume" in values and not values["volume"].is_integer():
            errors.append(f"{label}: volume must be an integer")
        if not tri and not row.get("symbol", "").strip():
            errors.append(f"{label}: blank exchange symbol")
        if not tri:
            security_id = row.get("security_id", "").strip()
            if not security_id:
                errors.append(f"{label}: blank stable security_id")
            elif not is_valid_isin(security_id):
                errors.append(f"{label}: security_id must be a valid ISIN (shape and check digit)")
        if row.get("verification_status", "").strip() != "VERIFIED":
            errors.append(f"{label}: source row is not VERIFIED")
        if not row.get("reviewer", "").strip() or not row.get("reviewed_at", "").strip():
            errors.append(f"{label}: independent reviewer sign-off missing")
        else:
            try:
                date.fromisoformat(row["reviewed_at"].strip())
            except ValueError:
                errors.append(f"{label}: reviewed_at must be an ISO calendar date")
        url = urlparse(row.get("source_url", "").strip())
        if url.scheme != "https" or not url.netloc:
            errors.append(f"{label}: source_url must be HTTPS")
        evidence_value = row.get("evidence_path", "").strip()
        if not evidence_value:
            errors.append(f"{label}: missing archived evidence path")
        digest = row.get("evidence_sha256", "").strip()
        digest_valid = len(digest) == 64 and all(
            ch in "0123456789abcdefABCDEF" for ch in digest
        )
        if not digest_valid:
            errors.append(f"{label}: evidence_sha256 must be a 64-character digest")
        if resolved_evidence_root is not None and evidence_value:
            relative_evidence = Path(evidence_value)
            if relative_evidence.is_absolute() or ".." in relative_evidence.parts:
                errors.append(f"{label}: archived evidence path must stay inside the evidence root")
                continue
            evidence_file = (resolved_evidence_root / relative_evidence).resolve()
            try:
                evidence_file.relative_to(resolved_evidence_root)
            except ValueError:
                errors.append(f"{label}: resolved archived evidence path escapes the evidence root")
                continue
            if evidence_file not in verified_evidence:
                if not evidence_file.is_file() or not digest_valid:
                    verified_evidence[evidence_file] = None
                else:
                    import hashlib

                    verified_evidence[evidence_file] = hashlib.sha256(
                        evidence_file.read_bytes()
                    ).hexdigest()
            actual_digest = verified_evidence[evidence_file]
            if actual_digest is None:
                errors.append(f"{label}: archived evidence file is missing or cannot be checked")
            elif actual_digest.lower() != digest.lower():
                errors.append(f"{label}: archived evidence SHA-256 mismatch")
    if not rows:
        errors.append(f"{path.name}: no verified historical observations; header-only is not data")
    return errors


def audit_price_data_readiness(reference_dir: Path = REFERENCE) -> dict:
    """Check data contracts and prerequisite gates without certifying data correctness."""
    reference_dir = Path(reference_dir)
    membership = audit_pit_readiness(reference_dir)
    aliases = audit_security_aliases(
        reference_dir / "security_symbol_aliases.csv", reference_dir
    )
    actions = audit_corporate_action_ledger(reference_dir / "corporate_actions.csv")

    ohlcv_path = reference_dir / "nifty50_pilot_ohlcv.csv"
    tri_path = reference_dir / "nifty50_tri.csv"
    ohlcv_rows, ohlcv_errors = _read(ohlcv_path, OHLCV_COLUMNS)
    tri_rows, tri_errors = _read(tri_path, TRI_COLUMNS)
    errors = list(ohlcv_errors) + list(tri_errors)
    evidence_root = reference_dir.resolve().parent.parent
    errors.extend(_audit_rows(ohlcv_path, ohlcv_rows, tri=False, evidence_root=evidence_root))
    errors.extend(_audit_rows(tri_path, tri_rows, tri=True, evidence_root=evidence_root))

    # These are prerequisite evidence gates, not data-quality assertions.
    if not membership["ready_for_pit_research"]:
        errors.append("Step 2 prerequisite blocked: point-in-time membership evidence is not ready")
    if not aliases["ready"]:
        errors.append("Step 3 prerequisite blocked: effective-dated security identity evidence is not ready")
    if not actions["valid"] or actions.get("unresolved_adjustment_factor_rows", 0):
        errors.append("corporate-action source ledger invalid or contains unresolved adjustment factors")
    if not actions.get("corporate_action_adjustment_verified", False):
        errors.append("corporate-action price adjustments have not been independently reconciled")
    return {
        "ready_for_price_and_benchmark_research": not errors and bool(ohlcv_rows) and bool(tri_rows),
        "ohlcv_rows": len(ohlcv_rows),
        "tri_rows": len(tri_rows),
        "membership_prerequisite_ready": membership["ready_for_pit_research"],
        "security_identity_prerequisite_ready": aliases["ready"],
        "corporate_action_evidence_valid": actions["valid"],
        "corporate_action_adjustment_verified": actions["corporate_action_adjustment_verified"],
        "errors": errors,
        "limitations": [
            "This structural audit does not authenticate exchange source documents or vendor data.",
            "OHLCV adjusted_close must be reconciled to official corporate-action terms before use.",
            "Nifty 50 TRI is distinct from the price index; do not substitute price-index values.",
            "No data is inferred, backfilled, or fabricated by this audit.",
        ],
    }


def main() -> int:
    report = audit_price_data_readiness()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready_for_price_and_benchmark_research"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
