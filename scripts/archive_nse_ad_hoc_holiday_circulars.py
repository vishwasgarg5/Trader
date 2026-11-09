#!/usr/bin/env python3
"""Archive NSE ad-hoc capital-market closure circulars identified by TRI gaps."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import time
import urllib.request
from urllib.parse import urlparse

REGISTER = pathlib.Path("data/reference/nifty50_tri_ad_hoc_closures.csv")
MANIFEST = pathlib.Path("data/reports/nifty50_tri_ad_hoc_closure_archive.json")

# Exact hostnames only: substring checks can misclassify lookalike domains.
OFFICIAL_NSE_HOSTS = {
    "nseindia.com",
    "www.nseindia.com",
    "archives.nseindia.com",
    "nsearchives.nseindia.com",
    "niftyindices.com",
    "www.niftyindices.com",
}


def is_official_nse_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in OFFICIAL_NSE_HOSTS


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


def build_manifest(records: list[dict], failures: list[dict],
                   corroborating_records: list[dict],
                   corroborating_failures: list[dict],
                   discovered_mirror_candidates: list[dict],
                   expected_count: int) -> dict:
    """Keep corroboration discoverable without treating it as the missing circular."""
    return {
        "experiment_id": "NIFTY50_PILOT_001",
        "purpose": "Archive additional NSE Capital Market closure and holiday-revision circulars identified in TRI diagnostics",
        "records": records,
        "failures": failures,
        "corroborating_records": corroborating_records,
        "corroborating_failures": corroborating_failures,
        "discovered_mirror_candidates": discovered_mirror_candidates,
        "archived_count": len(records),
        "expected_count": expected_count,
        "independent_review_status": "PENDING",
        "calendar_completeness": "NOT_CERTIFIED",
        "research_status": "RESEARCH_HOLD",
        "holdout_access_authorized": False,
    }


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
                "archive_status": ("ARCHIVED_OFFICIAL_HOST_PDF_SIGNATURE_VALID" if is_official_nse_url(successful_url) else "ARCHIVED_THIRD_PARTY_MIRROR_PDF_SIGNATURE_VALID"),
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
    discovered_mirror_candidates = [{
        "related_circular_reference": "NSE/CMTR/57285",
        "document_type": "THIRD_PARTY_MIRROR_OF_NSE_ORIGINAL_CIRCULAR",
        "source_url": "https://geplcapital.com/fundamental-research/649a873a2dbe6.1687848762.CMTR57285.pdf",
        "discovery_status": "DISCOVERED_CONTENT_INDEXED_NOT_ARCHIVED",
        "document_metadata": {
            "date": "2023-06-27",
            "circular_reference": "NSE/CMTR/57285",
            "circular_reference_number": "76/2023",
            "subject": "Change in Trading Holiday",
        },
        "sha256": None,
        "independent_review_status": "PENDING",
        "note": "Search-indexed PDF content identifies the original circular; raw bytes have not been acquired and hashed by this workflow.",
    }]
    report = build_manifest(
        records, failures, corroborating_records, corroborating_failures,
        discovered_mirror_candidates, len(sources)
    )
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
