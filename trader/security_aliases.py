"""Fail-closed validation for effective-dated security symbol identity records."""
from __future__ import annotations

import csv
import hashlib
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_COLUMNS = {
    "alias_id", "alias_symbol", "official_symbol", "security_id",
    "relation_type", "valid_from", "valid_to", "source_url",
    "source_document_path", "source_sha256", "verification_status", "reviewer", "reviewed_at",
}
RELATIONS = {
    "TICKER_RENAME_SAME_SECURITY", "VENDOR_ALIAS", "SEPARATE_SECURITY",
}
STATUSES = {"UNVERIFIED", "SAMPLE_ONLY", "VERIFIED"}


def audit_security_aliases(path: Path, evidence_root: Path | None = None) -> dict:
    """Validate alias semantics, effective dates, and archived source integrity.

    A valid ledger is necessary but not sufficient to prove vendor price-series
    continuity; independent security-master and market-data reconciliation is
    still required.
    """
    path = Path(path)
    root = Path(evidence_root) if evidence_root is not None else path.parent
    errors: list[str] = []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
            if missing:
                return {
                    "ready": False, "rows": 0,
                    "errors": [f"missing columns: {sorted(missing)}"],
                    "security_identity_independently_established": False,
                }
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        return {
            "ready": False, "rows": 0,
            "errors": [f"cannot read alias ledger ({type(exc).__name__})"],
            "security_identity_independently_established": False,
        }

    seen_ids: set[str] = set()
    intervals: dict[str, list[tuple[date, date | None, str, str]]] = {}
    for row in rows:
        alias_id = row.get("alias_id", "").strip()
        alias = row.get("alias_symbol", "").strip().upper()
        official = row.get("official_symbol", "").strip().upper()
        relation = row.get("relation_type", "").strip()
        status = row.get("verification_status", "").strip()
        label = alias_id or "<blank alias_id>"

        if not alias_id or alias_id in seen_ids:
            errors.append(f"{label}: blank or duplicate alias_id")
        seen_ids.add(alias_id)
        if not alias or not official:
            errors.append(f"{label}: alias_symbol and official_symbol are required")
        if relation not in RELATIONS:
            errors.append(f"{label}: unsupported relation_type")
        if status not in STATUSES:
            errors.append(f"{label}: unsupported verification_status")
        if relation in {"TICKER_RENAME_SAME_SECURITY", "VENDOR_ALIAS"} and alias == official:
            errors.append(f"{label}: alias and official symbols must differ for {relation}")
        if relation == "SEPARATE_SECURITY" and alias != official:
            errors.append(f"{label}: SEPARATE_SECURITY must retain its own symbol, not map to another security")

        try:
            start = date.fromisoformat(row.get("valid_from", "").strip())
        except ValueError:
            start = None
            errors.append(f"{label}: invalid valid_from date")
        end_text = row.get("valid_to", "").strip()
        try:
            end = date.fromisoformat(end_text) if end_text else None
        except ValueError:
            end = None
            errors.append(f"{label}: invalid valid_to date")
        if start is not None and end is not None and end <= start:
            errors.append(f"{label}: valid_to must be after valid_from")

        if alias and start is not None:
            intervals.setdefault(alias, []).append((start, end, official, label))

        if status != "VERIFIED":
            errors.append(f"{label}: identity mapping is not VERIFIED")
        else:
            if not row.get("security_id", "").strip():
                errors.append(f"{label}: VERIFIED mapping lacks stable security_id")
            if not row.get("reviewer", "").strip() or not row.get("reviewed_at", "").strip():
                errors.append(f"{label}: VERIFIED mapping lacks independent reviewer sign-off")
            else:
                try:
                    date.fromisoformat(row["reviewed_at"].strip())
                except ValueError:
                    errors.append(f"{label}: reviewed_at must be an ISO calendar date")
            url = row.get("source_url", "").strip()
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"{label}: VERIFIED mapping lacks an HTTPS source URL")
            relative = row.get("source_document_path", "").strip()
            rel = Path(relative)
            if not relative or rel.is_absolute() or ".." in rel.parts:
                errors.append(f"{label}: source document path must be a safe relative path")
            else:
                base = root.resolve()
                target = (base / rel).resolve()
                try:
                    target.relative_to(base)
                except ValueError:
                    errors.append(f"{label}: source document path escapes evidence root")
                else:
                    if not target.is_file():
                        errors.append(f"{label}: archived source document is missing ({relative})")
                    else:
                        digest = hashlib.sha256(target.read_bytes()).hexdigest()
                        expected = row.get("source_sha256", "").strip().lower()
                        if digest != expected:
                            errors.append(f"{label}: SHA-256 mismatch for {relative}")

    for alias, records in intervals.items():
        records.sort(key=lambda item: item[0])
        previous_end: date | None = None
        previous_official: str | None = None
        previous_label: str | None = None
        for start, end, official, label in records:
            if previous_end is None and previous_label is not None:
                errors.append(f"{label}: overlapping open-ended alias interval for {alias}")
            elif previous_end is not None and start < previous_end:
                if official != previous_official:
                    errors.append(
                        f"{label}: overlapping alias interval maps {alias} to multiple official symbols"
                    )
                else:
                    errors.append(f"{label}: overlapping duplicate alias interval for {alias}")
            if previous_end is None or end is None or end > previous_end:
                previous_end = end
                previous_official = official
                previous_label = label

    return {
        "ready": not errors and bool(rows),
        "rows": len(rows),
        "verified_rows": sum(row.get("verification_status", "").strip() == "VERIFIED" for row in rows),
        "errors": errors,
        "security_identity_independently_established": False,
    }
