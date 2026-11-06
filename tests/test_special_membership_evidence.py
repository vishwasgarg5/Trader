import csv
import hashlib
from pathlib import Path

from trader.membership_evidence import audit_special_membership_events


FIELDS = [
    "event_id", "index_name", "member_key", "phase", "announcement_date",
    "effective_date", "constituent_count", "price_treatment", "source_url",
    "source_document_path", "source_sha256", "verification_status",
    "reviewer", "reviewed_at", "notes",
]

EVENTS = [
    ["N50-2023-JIOFIN-DUMMY-ADD", "NIFTY50", "JIOFIN_SPINOFF_DUMMY",
     "ADD_DUMMY", "2023-07-17", "2023-07-20", "51",
     "SPOS_DERIVED_CONSTANT_PRICE", "https://nse.example/demerger.pdf"],
    ["N50-2023-JIOFIN-LIST", "NIFTY50", "JIOFIN",
     "REPLACE_DUMMY_WITH_LISTED", "2023-07-17", "2023-08-21", "51",
     "LISTED_MARKET_PRICE", "https://nse.example/listing.pdf"],
    ["N50-2023-JIOFIN-REMOVE", "NIFTY50", "JIOFIN",
     "REMOVE_LISTED", "2023-09-05", "2023-09-07", "50",
     "MARKET_PRICE_AT_REMOVAL", "https://nse.example/removal.pdf"],
]


def _write_ledger(root: Path, *, verified: bool) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = root / "source.pdf"
    source.write_bytes(b"official source fixture")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    path = root / "special_events.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        for event in EVENTS:
            writer.writerow(event + [
                "source.pdf", digest, "VERIFIED" if verified else "SAMPLE_ONLY",
                "independent-reviewer" if verified else "",
                "2026-11-06" if verified else "",
                "fixture; dummy security is a synthetic membership key",
            ])
    return path


def test_jiofin_special_membership_events_are_required_and_sample_only_fails_closed():
    root = Path(__file__).resolve().parents[1] / "data" / "reference"
    report = audit_special_membership_events(root / "nifty50_special_membership_events.csv")
    assert report["ready"] is False
    assert report["rows"] == 3
    assert report["verified_rows"] == 0
    assert any("not VERIFIED" in error for error in report["errors"])


def test_complete_archived_special_membership_evidence_passes(tmp_path):
    path = _write_ledger(tmp_path, verified=True)
    report = audit_special_membership_events(path)
    assert report["ready"] is True
    assert report["verified_rows"] == 3


def test_special_membership_rejects_missing_dummy_phase(tmp_path):
    path = _write_ledger(tmp_path, verified=True)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows[1:])
    report = audit_special_membership_events(path)
    assert report["ready"] is False
    assert any("required JIOFIN temporary-membership event is missing" in error for error in report["errors"])


def test_special_membership_rejects_bad_archived_source_digest(tmp_path):
    path = _write_ledger(tmp_path, verified=True)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["source_sha256"] = "0" * 64
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    report = audit_special_membership_events(path)
    assert report["ready"] is False
    assert any("SHA-256 mismatch" in error for error in report["errors"])
