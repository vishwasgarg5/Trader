"""Diagnostic reconstruction of a float-adjusted Nifty 50 price index.

Diagnostic only: requires supplied effective-dated inputs and an explicit
pre-registered tolerance. Never fits parameters or changes source ledgers.
TRI reconstruction is intentionally separate and not implemented here.
"""
from __future__ import annotations
import math
from datetime import date
from urllib.parse import urlparse


def _day(value):
    return date.fromisoformat(str(value).strip())


def _positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _reviewed(row):
    url = urlparse(str(row.get("source_url", "")).strip())
    digest = str(row.get("evidence_sha256", "")).strip()
    try:
        date.fromisoformat(str(row.get("reviewed_at", "")).strip())
        review_date_ok = True
    except (TypeError, ValueError):
        review_date_ok = False
    return (url.scheme == "https" and bool(url.netloc) and len(digest) == 64
            and all(c in "0123456789abcdefABCDEF" for c in digest)
            and bool(str(row.get("reviewer", "")).strip()) and review_date_ok)


def _active(row, day):
    try:
        start = _day(row["valid_from"])
        end_text = str(row.get("valid_to", "")).strip()
        end = _day(end_text) if end_text else None
        return start <= day and (end is None or day < end)
    except (KeyError, TypeError, ValueError):
        return False


def reconstruct_price_index(dates, membership, security_inputs, divisors,
                            official_levels, *, tolerance_points):
    """Compute sum(close * free_float_shares * IWF) / supplied divisor.

    Membership requires security_id, symbol, valid_from, valid_to,
    verification_status and reviewed provenance. Security inputs require
    security_id, date, close, free_float_shares, investible_weight_factor and
    reviewed provenance. Divisor and official-level rows require date, their
    numeric value and reviewed provenance. Divisor must already embody
    provider corporate-action adjustments; no adjustment is inferred or fit.
    """
    if _positive(tolerance_points) is None:
        return {"status": "INSUFFICIENT_INPUTS",
                "reason": "A positive pre-registered absolute point tolerance is required; no default is assumed.",
                "rows": [], "parameter_fitting": False,
                "membership_written": False, "tri_reconstructed": False}

    by_input, by_divisor, by_official = {}, {}, {}
    errors = []
    for row in membership:
        if row.get("verification_status") != "VERIFIED" or not _reviewed(row):
            errors.append(f"membership evidence is not verified/reviewed: {row.get('security_id', '<unknown>')}")
        try:
            start = _day(row["valid_from"])
            end_text = str(row.get("valid_to", "")).strip()
            end = _day(end_text) if end_text else None
            if end is not None and end <= start:
                errors.append("invalid membership interval")
        except (KeyError, TypeError, ValueError):
            errors.append("membership row has invalid effective dates")

    for row in security_inputs:
        try:
            day = _day(row["date"])
        except (KeyError, TypeError, ValueError):
            errors.append("security input has invalid date")
            continue
        sid = str(row.get("security_id", "")).strip()
        if not sid or not _reviewed(row):
            errors.append(f"security input lacks identity/provenance/reviewer: {sid or '<blank>'}")
        by_input.setdefault((day, sid), []).append(row)

    for rows, target, field in ((divisors, by_divisor, "divisor"),
                                (official_levels, by_official, "index_level")):
        for row in rows:
            try:
                day = _day(row["date"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{field} row has invalid date")
                continue
            target.setdefault(day, []).append(row)
            if not _reviewed(row):
                errors.append(f"{field} evidence lacks provenance/reviewer: {day}")

    results, mismatch, insufficient = [], False, bool(errors)
    for date_text in dates:
        try:
            day = _day(date_text)
        except (TypeError, ValueError):
            results.append({"date": str(date_text), "status": "INSUFFICIENT_INPUTS", "reason": "invalid requested date"})
            insufficient = True
            continue

        active = [r for r in membership if r.get("verification_status") == "VERIFIED"
                  and _reviewed(r) and _active(r, day)]
        ids = [str(r.get("security_id", "")).strip() for r in active]
        if len(active) != 50 or len(set(ids)) != 50 or not all(ids):
            results.append({"date": day.isoformat(), "status": "INSUFFICIENT_INPUTS",
                            "reason": f"expected exactly 50 distinct verified active securities; found {len(set(ids))}"})
            insufficient = True
            continue

        ds, os = by_divisor.get(day, []), by_official.get(day, [])
        if len(ds) != 1 or len(os) != 1:
            results.append({"date": day.isoformat(), "status": "INSUFFICIENT_INPUTS",
                            "reason": "exactly one divisor and one official level observation are required"})
            insufficient = True
            continue
        divisor, official = _positive(ds[0].get("divisor")), _positive(os[0].get("index_level"))
        if divisor is None or official is None or not _reviewed(ds[0]) or not _reviewed(os[0]):
            results.append({"date": day.isoformat(), "status": "INSUFFICIENT_INPUTS",
                            "reason": "divisor/official level is non-positive or lacks reviewed provenance"})
            insufficient = True
            continue

        total, missing = 0.0, []
        for sid in ids:
            rows = by_input.get((day, sid), [])
            if len(rows) != 1:
                missing.append(sid)
                continue
            row = rows[0]
            close, shares, iwf = (_positive(row.get(k)) for k in
                                  ("close", "free_float_shares", "investible_weight_factor"))
            if close is None or shares is None or iwf is None or iwf > 1.0 or not _reviewed(row):
                missing.append(sid)
                continue
            total += close * shares * iwf
        if missing:
            results.append({"date": day.isoformat(), "status": "INSUFFICIENT_INPUTS",
                            "reason": "missing, duplicate, invalid or unreviewed security inputs",
                            "missing_or_invalid_security_ids": sorted(missing)})
            insufficient = True
            continue

        reconstructed = total / divisor
        residual = reconstructed - official
        passed = abs(residual) <= float(tolerance_points)
        mismatch = mismatch or not passed
        results.append({"date": day.isoformat(), "status": "MATCH" if passed else "MISMATCH",
                        "reconstructed_level": reconstructed, "official_level": official,
                        "residual_points": residual, "absolute_residual_points": abs(residual),
                        "tolerance_points": float(tolerance_points), "constituent_count": 50})

    if not dates:
        insufficient = True
        errors.append("no requested dates supplied")
    status = "INSUFFICIENT_INPUTS" if insufficient else ("MISMATCH" if mismatch else "MATCH")
    return {"status": status, "rows": results, "errors": errors,
            "tolerance_points": float(tolerance_points), "interpretation": ("CROSS_SOURCE_CONSISTENCY_CHECKED" if status == "MATCH" else "NOT_ESTABLISHED"),
            "parameter_fitting": False,
            "membership_written": False, "tri_reconstructed": False,
            "limitations": [
                "A level match is a consistency check, not proof that constituent history is correct; offsetting errors can match.",
                "Divisor must be independently sourced and already reflect official corporate-action adjustments.",
                "This price-index calculation does not reconstruct Nifty 50 TRI or dividend reinvestment.",
                "Provenance shape is checked; source authenticity and reviewer independence are not authenticated.",
            ]}
