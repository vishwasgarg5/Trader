"""Probe public NSE daily bhavcopy and Nifty Indices notice endpoints.

This is a bounded access test, not a bulk downloader or a data-licence opinion.
It checks representative trading dates across the legacy/UDiFF format cutover,
plus primary index-notice PDFs. No files are retained.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from typing import Callable

MAX_BYTES = 25 * 1024 * 1024
TIMEOUT_SECONDS = 30
USER_AGENT = "Trader-Nifty50-Pilot-Archive-Probe/1.0 (research access check)"

LEGACY_TEMPLATE = (
    "https://archives.nseindia.com/content/historical/EQUITIES/"
    "{year}/{month}/cm{day}{month}{year}bhav.csv.zip"
)
UDIFF_TEMPLATE = (
    "https://nsearchives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip"
)

BHAVCOPY_SAMPLES = (
    ("legacy_2018_start", "2018-01-02", "legacy"),
    ("legacy_2020_midpoint", "2020-03-19", "legacy"),
    ("legacy_last_session_before_cutover", "2024-07-05", "legacy"),
    ("udiff_first_session_after_cutover", "2024-07-08", "udiff"),
)
NOTICE_SAMPLES = (
    ("nifty50_2018_constituent_notice",
     "https://www.niftyindices.com/Press_Release/ind_prs21022018.pdf"),
    ("nifty50_2020_superseding_notice",
     "https://www.niftyindices.com/Press_Release/ind_prs16032020.pdf"),
    ("nifty50_2024_constituent_notice",
     "https://www.niftyindices.com/Press_Release/ind_prs23082024.pdf"),
)


def bhavcopy_url(trade_date: str, format_name: str) -> str:
    from datetime import date

    day = date.fromisoformat(trade_date)
    if format_name == "legacy":
        return LEGACY_TEMPLATE.format(
            year=day.strftime("%Y"),
            month=day.strftime("%b").upper(),
            day=day.strftime("%d"),
        )
    if format_name == "udiff":
        return UDIFF_TEMPLATE.format(yyyymmdd=day.strftime("%Y%m%d"))
    raise ValueError(f"Unsupported bhavcopy format: {format_name}")


@dataclass
class ProbeResult:
    sample: str
    url: str
    status: str
    http_status: int | None = None
    bytes_received: int = 0
    sha256: str = ""
    content_type: str = ""
    detail: str = ""
    csv_member: str = ""
    csv_header: list[str] | None = None


def _get_bytes(url: str) -> tuple[bytes, int, str]:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        status = int(response.status)
        content_type = response.headers.get("Content-Type", "")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"response exceeds {MAX_BYTES} byte safety cap")
    return data, status, content_type


def probe_bhavcopy(sample: str, trade_date: str, format_name: str,
                   getter: Callable = _get_bytes) -> ProbeResult:
    url = bhavcopy_url(trade_date, format_name)
    result = ProbeResult(sample=sample, url=url, status="FAILED")
    try:
        payload, http_status, content_type = getter(url)
        result.http_status = http_status
        result.bytes_received = len(payload)
        result.sha256 = hashlib.sha256(payload).hexdigest()
        result.content_type = content_type
        if http_status != 200:
            result.detail = f"unexpected HTTP status {http_status}"
            return result
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise ValueError(f"ZIP CRC failure in {bad_member}")
            members = [name for name in archive.namelist()
                       if name.lower().endswith(".csv")]
            if not members:
                raise ValueError("ZIP contains no CSV member")
            result.csv_member = members[0]
            with archive.open(members[0]) as handle:
                header_line = handle.readline(64 * 1024).decode("utf-8-sig", errors="replace")
            result.csv_header = next(csv.reader([header_line]), [])
            if len(result.csv_header) < 5:
                raise ValueError("CSV header is missing or implausibly short")
        result.status = "PUBLIC_DOWNLOAD_AND_ZIP_VALID"
        result.detail = "Unauthenticated HTTP GET succeeded; ZIP CRC and CSV header checked."
    except urllib.error.HTTPError as exc:
        result.http_status = exc.code
        result.detail = f"HTTP error: {exc.code} {exc.reason}"
    except Exception as exc:  # network, ZIP, parse, and response-cap errors
        result.detail = f"{type(exc).__name__}: {exc}"
    return result


def probe_pdf(sample: str, url: str, getter: Callable = _get_bytes) -> ProbeResult:
    result = ProbeResult(sample=sample, url=url, status="FAILED")
    try:
        payload, http_status, content_type = getter(url)
        result.http_status = http_status
        result.bytes_received = len(payload)
        result.sha256 = hashlib.sha256(payload).hexdigest()
        result.content_type = content_type
        if http_status != 200:
            result.detail = f"unexpected HTTP status {http_status}"
        elif not payload.startswith(b"%PDF-"):
            result.detail = "HTTP 200 response is not a PDF signature"
        else:
            result.status = "PUBLIC_PDF_DOWNLOAD"
            result.detail = "Unauthenticated HTTP GET returned PDF bytes; content hash recorded."
    except urllib.error.HTTPError as exc:
        result.http_status = exc.code
        result.detail = f"HTTP error: {exc.code} {exc.reason}"
    except Exception as exc:
        result.detail = f"{type(exc).__name__}: {exc}"
    return result


def run_probe() -> dict:
    results = [
        probe_bhavcopy(name, trade_date, format_name)
        for name, trade_date, format_name in BHAVCOPY_SAMPLES
    ]
    results.extend(probe_pdf(name, url) for name, url in NOTICE_SAMPLES)
    passed = sum(item.status in {
        "PUBLIC_DOWNLOAD_AND_ZIP_VALID", "PUBLIC_PDF_DOWNLOAD"
    } for item in results)
    return {
        "probe": "NSE_PUBLIC_ARCHIVE_ACCESS",
        "scope": "4 representative bhavcopy dates and 3 Nifty Indices primary notice PDFs",
        "results": [asdict(item) for item in results],
        "passed": passed,
        "total": len(results),
        "all_samples_accessible": passed == len(results),
        "interpretation": (
            "Successful unauthenticated retrieval establishes access for these samples only; "
            "it does not prove complete 2018-2024 coverage, historical index snapshots, "
            "TRI coverage, redistribution rights, or archive completeness."
        ),
    }


def main() -> int:
    report = run_probe()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_samples_accessible"] else 1


if __name__ == "__main__":
    sys.exit(main())
