import csv
import hashlib
from pathlib import Path

import pytest

from trader.nifty_notice_register_archive import archive_register


FIELDS = [
    "notice_id",
    "source_url",
    "source_document_path",
    "source_sha256",
    "review_status",
    "reviewer",
    "reviewed_at",
    "notes",
]


class FakeResponse:
    def __init__(self, data: bytes, final_url: str):
        self.data = data
        self.final_url = final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self):
        return self.final_url

    def read(self, limit: int):
        return self.data[:limit]


def write_register(path: Path, row: dict) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def read_row(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.DictReader(handle))


def located_row(**overrides):
    row = {
        "notice_id": "NSE_CIRCULAR_FAOP58243_2023-09-05",
        "source_url": "https://nsearchives.nseindia.com/content/circulars/FAOP58243.pdf",
        "source_document_path": "",
        "source_sha256": "",
        "review_status": "LOCATED_NOT_ARCHIVED",
        "reviewer": "",
        "reviewed_at": "",
        "notes": (
            "Official NSE F&O circular confirms JIOFIN exclusion. "
            "Original PDF bytes still not archived or hashed; retain LOCATED_NOT_ARCHIVED "
            "until the actual PDF is committed and SHA-256 verified. Independent human review pending."
        ),
    }
    row.update(overrides)
    return row


def test_archives_located_circular_and_keeps_human_review_pending(tmp_path):
    register = tmp_path / "notice_register.csv"
    write_register(register, located_row())
    pdf = b"%PDF-1.7\nfixture source bytes"

    def opener(request, timeout):
        assert request.full_url.endswith("/FAOP58243.pdf")
        assert timeout == 30
        return FakeResponse(pdf, request.full_url)

    report = archive_register(register, tmp_path, opener=opener)
    row = read_row(register)
    path = tmp_path / row["source_document_path"]

    assert report["archived_count"] == 1
    assert report["register_rows"] == 1
    assert path.read_bytes() == pdf
    assert row["source_sha256"] == hashlib.sha256(pdf).hexdigest()
    assert row["review_status"] == "ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW"
    assert row["reviewer"] == ""
    assert row["reviewed_at"] == ""
    assert "Original PDF bytes still not archived" not in row["notes"]
    assert "Independent human review remains pending." in row["notes"]


def test_archive_is_idempotent_and_verifies_existing_hash(tmp_path):
    register = tmp_path / "notice_register.csv"
    pdf = b"%PDF-1.4\nfixture"
    digest = hashlib.sha256(pdf).hexdigest()
    relative = "data/reference/source_documents/notice.pdf"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(pdf)
    write_register(
        register,
        located_row(
            source_document_path=relative,
            source_sha256=digest,
            review_status="ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW",
            notes="Archived and awaiting independent review.",
        ),
    )

    def unexpected_download(*args, **kwargs):
        raise AssertionError("A verified archived PDF must not be downloaded again")

    report = archive_register(register, tmp_path, opener=unexpected_download)
    assert report["archived_count"] == 0
    assert report["verified_existing_count"] == 1
    assert report["changed"] is False


def test_refuses_unapproved_host_before_network_access(tmp_path):
    register = tmp_path / "notice_register.csv"
    write_register(register, located_row(source_url="https://example.com/FAOP58243.pdf"))

    def unexpected_download(*args, **kwargs):
        raise AssertionError("Unapproved host must be rejected before network access")

    with pytest.raises(ValueError, match="non-approved official source URL"):
        archive_register(register, tmp_path, opener=unexpected_download)


def test_rejects_redirect_to_unapproved_host(tmp_path):
    register = tmp_path / "notice_register.csv"
    write_register(register, located_row())
    pdf = b"%PDF-1.4\nfixture"

    def opener(request, timeout):
        return FakeResponse(pdf, "https://example.com/redirected.pdf")

    with pytest.raises(ValueError, match="Unexpected redirect host"):
        archive_register(register, tmp_path, opener=opener)


def test_rejects_non_pdf_response(tmp_path):
    register = tmp_path / "notice_register.csv"
    write_register(register, located_row())

    def opener(request, timeout):
        return FakeResponse(b"not a PDF", request.full_url)

    with pytest.raises(ValueError, match="not a PDF"):
        archive_register(register, tmp_path, opener=opener)


def test_existing_hash_mismatch_fails_closed_without_overwrite(tmp_path):
    register = tmp_path / "notice_register.csv"
    relative = "data/reference/source_documents/notice.pdf"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    original = b"%PDF-1.4\ncommitted bytes"
    target.write_bytes(original)
    write_register(
        register,
        located_row(
            source_document_path=relative,
            source_sha256=hashlib.sha256(b"%PDF-1.4\ndifferent bytes").hexdigest(),
            review_status="ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW",
        ),
    )

    with pytest.raises(ValueError, match="Source SHA-256 mismatch"):
        archive_register(register, tmp_path, opener=lambda *a, **k: None)
    assert target.read_bytes() == original
