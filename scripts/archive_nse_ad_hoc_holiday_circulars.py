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


def download(urls: list[str]) -> tuple[bytes, str]:
    last_error = None
    for url in urls:
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Nifty50ResearchEvidence/1.0)",
            "Referer": "https://www.nseindia.com/",
            "Accept": "application/pdf,*/*",
        })
        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    body = response.read()
                    if response.status != 200 or not body.startswith(b"%PDF-"):
                        raise ValueError(f"not a PDF (HTTP {response.status}, {len(body)} bytes)")
                    return body, url
            except Exception as exc:
                last_error = exc
                time.sleep(2 ** attempt)
    raise RuntimeError(str(last_error))


def main() -> int:
    records, failures, corroborating_records, corroborating_failures = [], [], [], []
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        sources = list(csv.DictReader(handle))
    for source in sources:
        path = pathlib.Path(source["archive_path"])
        try:
            urls = [source["source_url"]]
            if source["circular_reference"] == "NSE/CMTR/57285":
                urls.extend([
                    "https://archives.nseindia.com/content/circulars/CMTR57285.pdf",
                    "https://geplcapital.com/fundamental-research/649a873a2dbe6.1687848762.CMTR57285.pdf",
                ])
            body, successful_url = download(urls)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            records.append({
                **source,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "downloaded_from_url": successful_url,
                "archive_status": ("ARCHIVED_OFFICIAL_HOST_PDF_SIGNATURE_VALID" if "nseindia.com" in successful_url else "ARCHIVED_THIRD_PARTY_MIRROR_PDF_SIGNATURE_VALID"),
                "independent_review_status": "PENDING",
            })
        except Exception as exc:
            failures.append({
                "session_date": source["session_date"],
                "circular_reference": source["circular_reference"],
                "event_type": source["event_type"],
                "source_url": source["source_url"],
                "error": str(exc),
            })
            if source["circular_reference"] == "NSE/CMTR/57285":
                press_release_url = "https://niftyindices.com/Press_Release/ind_prs27062023.pdf"
                press_release_path = pathlib.Path(
                    "data/reference/source_documents/nse_ad_hoc_holiday_circulars/"
                    "2023-06-27_NSE_Indices_press_release.pdf"
                )
                try:
                    body, successful_url = download([press_release_url])
                    press_release_path.parent.mkdir(parents=True, exist_ok=True)
                    press_release_path.write_bytes(body)
                    corroborating_records.append({
                        "related_circular_reference": "NSE/CMTR/57285",
                        "document_type": "OFFICIAL_NSE_INDICES_PRESS_RELEASE_CORROBORATION_NOT_CIRCULAR",
                        "source_url": press_release_url,
                        "downloaded_from_url": successful_url,
                        "archive_path": press_release_path.as_posix(),
                        "bytes": len(body),
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "archive_status": "ARCHIVED_OFFICIAL_NSE_INDICES_PDF_SIGNATURE_VALID",
                        "independent_review_status": "PENDING",
                    })
                except Exception as corroboration_error:
                    corroborating_failures.append({
                        "related_circular_reference": "NSE/CMTR/57285",
                        "source_url": press_release_url,
                        "error": str(corroboration_error),
                    })
    report = {
        "experiment_id": "NIFTY50_PILOT_001",
        "purpose": "Archive additional NSE Capital Market closure and holiday-revision circulars identified in TRI diagnostics",
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
    return 0 if not any(row.get("event_type") == "AD_HOC_CLOSURE" for row in failures) and len(records) + len(failures) == len(sources) else 1


if __name__ == "__main__":
    raise SystemExit(main())
