#!/usr/bin/env python3
"""Acquire NSE circular PDFs cited by the Nifty 50 TRI weekend review.

A successful HTTP/PDF check and SHA-256 digest establish archival integrity only;
they do not independently authenticate the circular or the TRI observation.
"""
from __future__ import annotations
import hashlib, json, os, pathlib, sys, time, urllib.error, urllib.request

ROOT = pathlib.Path("data/reference/source_documents/nse_circulars")
MANIFEST = pathlib.Path("data/reports/nifty50_tri_weekend_circular_archive.json")
SOURCES = [
    ("2019-10-27", "NSE_CMTR_42403", "https://nsearchives.nseindia.com/content/circulars/CMTR42403.pdf"),
    ("2020-02-01", "NSE_CMTR_43290", "https://nsearchives.nseindia.com/content/circulars/CMTR43290.pdf"),
    ("2020-11-14", "NSE_CMTR_46230", "https://nsearchives.nseindia.com/content/circulars/CMTR46230.pdf"),
    ("2023-11-12", "NSE_ISC_59313", "https://nsearchives.nseindia.com/content/circulars/ISC59313.pdf"),
    ("2024-01-20", "NSE_MSD_60340", "https://nsearchives.nseindia.com/content/circulars/MSD60340.pdf"),
    ("2024-03-02", "NSE_MSD_60677", "https://nsearchives.nseindia.com/content/circulars/MSD60677.pdf"),
    ("2024-05-18", "NSE_MSD_61893", "https://nsearchives.nseindia.com/content/circulars/MSD61893.pdf"),
]

def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Nifty50ResearchEvidence/1.0)",
        "Referer": "https://www.niftyindices.com/reports",
        "Accept": "application/pdf,*/*",
    })
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read()
                if response.status != 200 or not body.startswith(b"%PDF-"):
                    raise ValueError(f"response is not a PDF (status={response.status}, bytes={len(body)})")
                return body
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed: {last}")

def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    records, failures = [], []
    for session_date, ref, url in SOURCES:
        filename = f"{session_date}_{ref}.pdf"
        path = ROOT / filename
        try:
            body = fetch(url)
            path.write_bytes(body)
            records.append({
                "session_date": session_date, "circular_reference": ref,
                "source_url": url, "archive_path": path.as_posix(),
                "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                "download_status": "ARCHIVED_PDF_SIGNATURE_VALID",
                "independent_review_status": "PENDING",
            })
        except Exception as exc:
            failures.append({"session_date": session_date, "circular_reference": ref,
                             "source_url": url, "download_status": "FAILED",
                             "error": str(exc)})
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "purpose": "Archive source circulars for weekend-dated TRI observations",
        "archived_count": len(records), "expected_count": len(SOURCES),
        "records": records, "failures": failures,
        "interpretation": "PDF signature and SHA-256 verify downloaded-byte integrity only; they do not prove publisher authenticity, full circular semantics, or TRI correctness.",
        "research_status": "RESEARCH_HOLD",
        "holdout_access_authorized": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"archived_count": len(records), "expected_count": len(SOURCES), "failures": failures}, indent=2))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
