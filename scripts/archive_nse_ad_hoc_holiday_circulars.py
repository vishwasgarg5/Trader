#!/usr/bin/env python3
"""Archive NSE ad-hoc capital-market closure circulars identified by TRI gaps."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import time
import urllib.request

REGISTER = pathlib.Path("data/reference/nifty50_tri_ad_hoc_closures.csv")
MANIFEST = pathlib.Path("data/reports/nifty50_tri_ad_hoc_closure_archive.json")


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Nifty50ResearchEvidence/1.0)",
        "Referer": "https://www.nseindia.com/",
        "Accept": "application/pdf,*/*",
    })
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read()
                if response.status != 200 or not body.startswith(b"%PDF-"):
                    raise ValueError(f"not a PDF (HTTP {response.status}, {len(body)} bytes)")
                return body
        except Exception as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(str(last_error))


def main() -> int:
    records, failures = [], []
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        sources = list(csv.DictReader(handle))
    for source in sources:
        path = pathlib.Path(source["archive_path"])
        try:
            body = download(source["source_url"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            records.append({
                **source,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "archive_status": "ARCHIVED_PDF_SIGNATURE_VALID",
                "independent_review_status": "PENDING",
            })
        except Exception as exc:
            failures.append({
                "session_date": source["session_date"],
                "circular_reference": source["circular_reference"],
                "source_url": source["source_url"],
                "error": str(exc),
            })
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "purpose": "Archive additional NSE Capital Market closure circulars identified in TRI gap diagnostics",
        "records": records,
        "failures": failures,
        "archived_count": len(records),
        "expected_count": len(sources),
        "independent_review_status": "PENDING",
        "calendar_completeness": "NOT_CERTIFIED",
        "research_status": "RESEARCH_HOLD",
        "holdout_access_authorized": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "archived_count": len(records),
        "expected_count": len(sources),
        "failures": failures,
    }, indent=2))
    return 0 if not failures and len(records) == len(sources) else 1


if __name__ == "__main__":
    raise SystemExit(main())
