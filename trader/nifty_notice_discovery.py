"""Discover NSE Indices press releases and archive review-relevant source PDFs.

Discovery is deliberately conservative: every discovered archive entry is recorded,
but only title-keyword candidates are downloaded. The tool never infers a Nifty 50
membership change or marks a notice VERIFIED. Automated output is triage evidence,
not independent review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ARCHIVE_URL = "https://www.niftyindices.com/press-release"
ALLOWED_HOSTS = {"www.niftyindices.com", "niftyindices.com", "nsearchives.nseindia.com"}
YEARS = range(2018, 2025)
INVENTORY = Path("data/reference/nifty50_annual_notice_inventory.csv")
SOURCE_DIR = Path("data/reference/source_documents")
REPORT = Path("data/reports/nifty50_notice_discovery.json")
FIELDS = [
    "notice_id", "year", "announcement_date", "effective_date", "source_role",
    "source_url", "observed_nifty50_effect", "source_document_path",
    "source_sha256", "review_status", "notes",
]
DATE_PATTERNS = (
    "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y", "%d %B %Y",
)
DATE_RE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b|\b\d{1,2}-[A-Za-z]{3}-\d{4}\b", re.I)
PDF_RE = re.compile(r"""(?:https?://)?[^\\s"'<>()]*?\\.pdf(?:\\?[^\\s"'<>()]*)?""", re.I)
REVIEW_TERMS = re.compile(
    r"replacement|replacements|inclusion|inclusions|exclusion|exclusions|"
    r"corporate action|demerger|merger|reconstitution|rebalanc|"
    r"methodolog|criteria|index change|changes in indices|changes in nifty",
    re.I,
)


def parse_date(value: str):
    value = value.strip()
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


class PressReleaseParser(HTMLParser):
    """Extract PDF anchors and associate them with the closest preceding date."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current_date = None
        self.anchor = None
        self.entries = []
        self.unparsed_pdf_links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        values = [attrs.get(k, "") for k in ("href", "onclick", "data-href", "data-url")]
        candidates = []
        for value in values:
            if not value:
                continue
            candidates.extend(PDF_RE.findall(value.replace("&amp;", "&")))
            if value.lower().endswith(".pdf"):
                candidates.append(value)
        if tag.lower() == "a":
            self.anchor = {"title": [], "urls": list(dict.fromkeys(candidates)), "date": self.current_date}
        elif candidates:
            for url in dict.fromkeys(candidates):
                self.unparsed_pdf_links.append(url)

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return
        match = DATE_RE.search(text)
        if match:
            parsed = parse_date(match.group(0))
            if parsed:
                self.current_date = parsed
        if self.anchor is not None:
            self.anchor["title"].append(text)

    def handle_endtag(self, tag):
        if tag.lower() != "a" or self.anchor is None:
            return
        title = " ".join(self.anchor["title"]).strip()
        for raw_url in self.anchor["urls"]:
            self.entries.append({
                "date": self.anchor["date"],
                "title": title,
                "url": raw_url,
            })
        self.anchor = None


def _request(url: str, *, max_bytes: int = 30_000_000) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Refusing source outside approved NSE Indices hosts: {url}")
    request = urllib.request.Request(
        url, headers={"User-Agent": "TraderNifty50EvidenceDiscovery/1.0"}
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Unexpected redirect outside approved hosts: {response.geturl()}")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"Source exceeds {max_bytes} byte limit: {url}")
    return data


def discover_entries(html: str, start_year: int = 2018, end_year: int = 2024):
    parser = PressReleaseParser()
    parser.feed(html)
    unique = {}
    unparsed = []
    for item in parser.entries:
        url = urllib.parse.urljoin(ARCHIVE_URL, item["url"]).replace("&amp;", "&")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            continue
        date = item["date"]
        if date is None:
            unparsed.append({"url": url, "title": item["title"]})
            continue
        if not start_year <= date.year <= end_year:
            continue
        key = url
        unique[key] = {
            "date": date,
            "title": item["title"],
            "url": url,
            "review_candidate": bool(REVIEW_TERMS.search(item["title"])),
        }
    return sorted(unique.values(), key=lambda x: (x["date"], x["url"])), unparsed


def _load_inventory(path: Path):
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Unexpected inventory schema in {path}")
        return {row["source_url"]: row for row in reader if row.get("source_url")}


def run_discovery(
    inventory_path: Path = INVENTORY,
    source_dir: Path = SOURCE_DIR,
    report_path: Path = REPORT,
    start_year: int = 2018,
    end_year: int = 2024,
    archive_candidates: bool = True,
):
    html = _request(ARCHIVE_URL, max_bytes=20_000_000).decode("utf-8", errors="replace")
    discovered, unparsed = discover_entries(html, start_year, end_year)
    existing = _load_inventory(inventory_path)
    new_count = 0
    candidate_count = 0
    archived_count = 0
    failures = []
    for item in discovered:
        if not item["review_candidate"]:
            continue
        candidate_count += 1
        url = item["url"]
        row = existing.get(url)
        if row is None:
            digest_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            notice_id = f"NSE-ARCHIVE-{item['date'].isoformat()}-{digest_id}"
            row = {
                "notice_id": notice_id,
                "year": str(item["date"].year),
                "announcement_date": item["date"].isoformat(),
                "effective_date": "",
                "source_role": "DISCOVERED_ARCHIVE_CANDIDATE",
                "source_url": url,
                "observed_nifty50_effect": "UNCLASSIFIED_REVIEW_REQUIRED",
                "source_document_path": "",
                "source_sha256": "",
                "review_status": "DISCOVERED_UNREVIEWED",
                "notes": f"Archive title: {item['title']}. Automated title-keyword candidate only; inspect PDF and classify index scope.",
            }
            existing[url] = row
            new_count += 1
        else:
            # Never overwrite a human classification or a previously assigned notice ID.
            if not row.get("notes", "").strip():
                row["notes"] = f"Archive title: {item['title']}."
        if archive_candidates and (not row.get("source_document_path") or not row.get("source_sha256")):
            try:
                data = _request(url)
                if not data.startswith(b"%PDF-"):
                    raise ValueError("Downloaded source does not have a PDF signature")
                digest = hashlib.sha256(data).hexdigest()
                path = source_dir / f"{row['notice_id']}.pdf"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                row["source_document_path"] = path.as_posix()
                row["source_sha256"] = digest
                archived_count += 1
            except Exception as exc:  # retain discovery row and report the exact failure
                failures.append({"notice_id": row["notice_id"], "url": url, "error": str(exc)})

    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    with inventory_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(existing.values(), key=lambda r: (r["year"], r["announcement_date"], r["notice_id"])))

    report = {
        "archive_url": ARCHIVE_URL,
        "scope": {"start_year": start_year, "end_year": end_year},
        "archive_entries_discovered": len(discovered),
        "review_keyword_candidates": candidate_count,
        "new_inventory_rows": new_count,
        "candidate_pdfs_archived_this_run": archived_count,
        "unparsed_pdf_links": unparsed,
        "archive_failures": failures,
        "classification_policy": "No Nifty 50 effect is inferred automatically; all new rows remain UNCLASSIFIED_REVIEW_REQUIRED.",
        "coverage_complete": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--no-archive", action="store_true")
    args = parser.parse_args()
    report = run_discovery(
        start_year=args.start_year,
        end_year=args.end_year,
        archive_candidates=not args.no_archive,
    )
    print(json.dumps(report, indent=2))
    if report["archive_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
