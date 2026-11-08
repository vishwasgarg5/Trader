#!/usr/bin/env python3
"""Acquire NSE Capital Market holiday circulars for the 2018-2024 TRI audit.

PDF signature and SHA-256 checks establish downloaded-byte integrity only.
They do not independently authenticate publisher identity or circular meaning.
"""
from __future__ import annotations
import hashlib, json, pathlib, time, urllib.request

ROOT = pathlib.Path("data/reference/source_documents/nse_holiday_circulars")
MANIFEST = pathlib.Path("data/reports/nifty50_tri_holiday_circular_archive.json")
SOURCES = [
    (2018, "NSE_CMTR_36475", "https://nsearchives.nseindia.com/content/circulars/CMTR36475.pdf"),
    (2019, "NSE_CMTR_39612", "https://nsearchives.nseindia.com/content/circulars/CMTR39612.pdf"),
    (2020, "NSE_CMTR_42877", "https://nsearchives.nseindia.com/content/circulars/CMTR42877.pdf"),
    (2021, "NSE_CMTR_46623", "https://nsearchives.nseindia.com/content/circulars/CMTR46623.pdf"),
    (2022, "NSE_CMTR_50560", "https://nsearchives.nseindia.com/content/circulars/CMTR50560.pdf"),
    (2023, "NSE_CMTR_54757", "https://nsearchives.nseindia.com/content/circulars/CMTR54757.pdf"),
    (2024, "NSE_CMTR_59722", "https://nsearchives.nseindia.com/content/circulars/CMTR59722.pdf"),
]

def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Nifty50ResearchEvidence/1.0)",
        "Referer": "https://www.nseindia.com/",
        "Accept": "application/pdf,*/*",
    })
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                body = response.read()
                if response.status != 200 or not body.startswith(b"%PDF-"):
                    raise ValueError(f"not a PDF (HTTP {response.status}, {len(body)} bytes)")
                return body
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(str(last))

def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    records, failures = [], []
    for year, ref, url in SOURCES:
        path = ROOT / f"{year}_{ref}.pdf"
        try:
            body = download(url)
            path.write_bytes(body)
            records.append({
                "year": year, "circular_reference": ref, "source_url": url,
                "archive_path": path.as_posix(), "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "download_status": "ARCHIVED_PDF_SIGNATURE_VALID",
                "independent_review_status": "PENDING",
            })
        except Exception as exc:
            failures.append({"year": year, "circular_reference": ref,
                             "source_url": url, "download_status": "FAILED",
                             "error": str(exc)})
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "purpose": "Archive annual NSE Capital Market trading-holiday circulars for 2018-2024 calendar reconciliation",
        "archived_count": len(records), "expected_count": len(SOURCES),
        "covered_years": [r["year"] for r in records],
        "records": records, "failures": failures,
        "interpretation": "Archival does not itself extract or certify the full calendar; independent review and session-level reconciliation remain required.",
        "calendar_completeness": "NOT_CERTIFIED",
        "independent_review_status": "PENDING",
        "research_status": "RESEARCH_HOLD",
        "holdout_access_authorized": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"archived_count": len(records), "expected_count": len(SOURCES),
                      "covered_years": [r["year"] for r in records], "failures": failures}, indent=2))

if __name__ == "__main__":
    main()
