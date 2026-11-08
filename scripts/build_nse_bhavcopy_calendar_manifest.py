#!/usr/bin/env python3
"""Build a candidate NSE session-date manifest from acquired NIFTY 50 TRI observations.

TRI dates are an official-source cross-check, not a certified exchange calendar
until the separate holiday/special-session review is signed off.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRI_PATH = ROOT / "data/reference/nifty50_tri.csv"
DEFAULT_OUTPUT = ROOT / "data/tmp/nse_bhavcopy_calendar_candidate.csv"
FIELDS = [
    "trade_date", "calendar_source_url", "calendar_source_path",
    "calendar_source_sha256", "calendar_review_status", "tri_verification_status",
]


def build_manifest(tri_path: Path, dates: set[str] | None = None) -> list[dict]:
    with tri_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"session_date", "source_url", "evidence_path", "evidence_sha256", "verification_status"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"TRI file requires columns: {sorted(required)}")
        rows = list(reader)
    manifest, seen, verified_sources = [], set(), {}
    for row in rows:
        day = date.fromisoformat(row["session_date"]).isoformat()
        if dates is not None and day not in dates:
            continue
        if day in seen:
            raise ValueError(f"duplicate TRI session date: {day}")
        seen.add(day)
        source = (ROOT / row["evidence_path"]).resolve()
        source.relative_to(ROOT.resolve())
        if not source.is_file():
            raise ValueError(f"TRI source evidence missing for {day}: {row['evidence_path']}")
        expected = row["evidence_sha256"].strip().lower()
        if source not in verified_sources:
            verified_sources[source] = hashlib.sha256(source.read_bytes()).hexdigest()
        if verified_sources[source] != expected:
            raise ValueError(f"TRI source SHA-256 mismatch for {day}: {row['evidence_path']}")
        if not row["source_url"].startswith("https://"):
            raise ValueError(f"TRI source URL is not HTTPS for {day}")
        manifest.append({
            "trade_date": day,
            "calendar_source_url": row["source_url"],
            "calendar_source_path": row["evidence_path"],
            "calendar_source_sha256": expected,
            "calendar_review_status": "CANDIDATE_UNREVIEWED_TRI_OBSERVATION",
            "tri_verification_status": row["verification_status"],
        })
    if dates is not None and seen != dates:
        raise ValueError(f"requested dates missing from TRI source: {sorted(dates - seen)}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tri", type=Path, default=TRI_PATH)
    parser.add_argument("--dates", help="comma-separated exact dates; omit to include all TRI dates")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    requested = {date.fromisoformat(x.strip()).isoformat() for x in args.dates.split(",")} if args.dates else None
    rows = build_manifest(args.tri, requested)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"candidate_session_dates={len(rows)}")
    print(f"calendar_review_status=CANDIDATE_UNREVIEWED_TRI_OBSERVATION")
    print(f"output={args.output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
