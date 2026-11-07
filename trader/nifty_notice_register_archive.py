"""Archive located official exchange circulars in the curated Nifty 50 notice register.

This only upgrades source-byte archival status. It never records human approval.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path, PurePosixPath
import urllib.parse
import urllib.request

REGISTER = Path("data/reference/nifty50_notice_register.csv")
SOURCE_ROOT = "data/reference/source_documents/"
ALLOWED_HOSTS = {
    "nsearchives.nseindia.com",
    "archives.nseindia.com",
    "www.niftyindices.com",
    "niftyindices.com",
}
MAX_BYTES = 25 * 1024 * 1024
REQUIRED_FIELDS = {
    "notice_id",
    "source_url",
    "source_document_path",
    "source_sha256",
    "review_status",
    "reviewer",
    "reviewed_at",
    "notes",
}
LOCATED_STATUS = "LOCATED_NOT_ARCHIVED"
ARCHIVED_STATUS = "ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW"


def _relative_source_path(value: str, notice_id: str) -> PurePosixPath:
    raw = value.strip() or f"{SOURCE_ROOT}NOTICE-{notice_id}.pdf"
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe source_document_path for {notice_id}: {raw}")
    if not relative.as_posix().startswith(SOURCE_ROOT):
        raise ValueError(f"Source path must be under {SOURCE_ROOT}: {raw}")
    return relative


def _download_pdf(url: str, opener) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Refusing non-approved official source URL: {url}")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TraderResearchEvidenceArchiver/1.0"},
    )
    with opener(request, timeout=30) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Unexpected redirect host for {url}: {response.geturl()}")
        data = response.read(MAX_BYTES + 1)

    if len(data) > MAX_BYTES:
        raise ValueError(f"Source PDF exceeds 25 MiB limit: {url}")
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"Official source response is not a PDF: {url}")
    return data


def archive_register(
    register_path: Path = REGISTER,
    root: Path = Path("."),
    opener=None,
) -> dict:
    """Archive any located-but-unarchived register row and verify all existing rows."""
    opener = opener or urllib.request.urlopen
    with register_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields:
            raise ValueError(f"Notice register has no header: {register_path}")
        missing = REQUIRED_FIELDS - set(fields)
        if missing:
            raise ValueError(f"Notice register missing fields: {sorted(missing)}")
        rows = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Notice register has extra CSV columns on line {line_number}")
            rows.append(row)

    notice_ids = [row["notice_id"].strip() for row in rows]
    if len(notice_ids) != len(set(notice_ids)):
        raise ValueError("Notice register contains duplicate notice_id values")

    changed = False
    archived = []
    verified_existing = 0

    for row in rows:
        notice_id = row["notice_id"].strip()
        url = row["source_url"].strip()
        relative = _relative_source_path(row.get("source_document_path", ""), notice_id)
        target = root.joinpath(*relative.parts)
        expected = row.get("source_sha256", "").strip().lower()
        status = row.get("review_status", "").strip()

        if status == LOCATED_STATUS:
            data = _download_pdf(url, opener)
            digest = hashlib.sha256(data).hexdigest()
            if target.exists():
                existing = target.read_bytes()
                if existing != data:
                    raise ValueError(
                        f"Existing source bytes differ from official download for {notice_id}; "
                        "refusing to overwrite evidence."
                    )
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

            row["source_document_path"] = relative.as_posix()
            row["source_sha256"] = digest
            row["review_status"] = ARCHIVED_STATUS
            note = (row.get("notes") or "").strip()
            stale = (
                "Original PDF bytes still not archived or hashed; retain LOCATED_NOT_ARCHIVED "
                "until the actual PDF is committed and SHA-256 verified."
            )
            note = note.replace(stale, "").strip(" ;")
            archive_note = (
                f"Original official PDF archived at {relative.as_posix()} with SHA-256 "
                f"{digest}, computed from downloaded PDF bytes. Independent human review remains pending."
            )
            if archive_note not in note:
                note = f"{note} {archive_note}".strip()
            row["notes"] = note
            # Deliberately leave reviewer/reviewed_at unchanged: archival is not approval.
            changed = True
            archived.append({
                "notice_id": notice_id,
                "source_document_path": relative.as_posix(),
                "source_sha256": digest,
            })
            print(f"{notice_id}: archived {len(data)} bytes sha256={digest}")
            continue

        if not target.is_file():
            raise ValueError(
                f"Missing archived PDF for {notice_id} with status {status}; "
                "only LOCATED_NOT_ARCHIVED rows may be newly downloaded automatically."
            )
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if not expected or actual != expected:
            raise ValueError(
                f"Source SHA-256 mismatch for {notice_id}: expected={expected or '<blank>'} actual={actual}"
            )
        if not row.get("source_document_path", "").strip():
            raise ValueError(f"Archived source path missing for {notice_id}")
        verified_existing += 1

    if changed:
        with register_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    return {
        "register_rows": len(rows),
        "archived_count": len(archived),
        "verified_existing_count": verified_existing,
        "changed": changed,
        "archived": archived,
    }


def main() -> None:
    report = archive_register()
    print(
        "Curated notice-register archive complete: "
        f"{report['archived_count']} newly archived, "
        f"{report['verified_existing_count']} existing PDFs hash-verified, "
        f"{report['register_rows']} register rows."
    )


if __name__ == "__main__":
    main()
