import csv
import hashlib
from pathlib import Path

from trader.security_aliases import audit_security_aliases, is_valid_isin


FIELDS = [
    "alias_id", "alias_symbol", "official_symbol", "security_id",
    "relation_type", "valid_from", "valid_to", "source_url",
    "source_document_path", "source_sha256", "verification_status", "notes", "reviewer", "reviewed_at",
]


def _write_ledger(root: Path, rows: list[dict]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "aliases.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return root / "aliases.csv"


def _verified_row(root: Path, **overrides) -> dict:
    source = root / "source.pdf"
    source.write_bytes(b"official source fixture")
    row = {
        "alias_id": "A1",
        "alias_symbol": "OLD",
        "official_symbol": "NEW",
        "security_id": "INE214T01019",
        "relation_type": "TICKER_RENAME_SAME_SECURITY",
        "valid_from": "2024-01-01",
        "valid_to": "",
        "source_url": "https://www.nseindia.com/source.pdf",
        "source_document_path": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "verification_status": "VERIFIED",
        "notes": "fixture",
        "reviewer": "independent-reviewer",
        "reviewed_at": "2024-01-02",
    }
    row.update(overrides)
    return row


def test_isin_validation_checks_shape_and_luhn_digit():
    assert is_valid_isin("INE214T01019")
    assert is_valid_isin("INE155A01022")
    assert is_valid_isin("INE1TAE01010")
    assert not is_valid_isin("INE214T01010")
    assert not is_valid_isin("not-an-isin")
    assert not is_valid_isin("INE214T0101")


def test_verified_alias_requires_archived_source_and_stable_security_id(tmp_path):
    row = _verified_row(tmp_path)
    path = _write_ledger(tmp_path, [row])
    report = audit_security_aliases(path)
    assert report["ready"] is True
    assert report["verified_rows"] == 1
    assert report["security_identity_independently_established"] is False


def test_unverified_current_alias_register_fails_closed():
    root = Path(__file__).resolve().parents[1] / "data" / "reference"
    report = audit_security_aliases(root / "security_symbol_aliases.csv", root)
    assert report["ready"] is False
    assert report["rows"] == 3
    assert any("not VERIFIED" in error for error in report["errors"])


def test_separate_security_cannot_be_mapped_as_an_alias(tmp_path):
    row = _verified_row(
        tmp_path,
        alias_symbol="TMCV",
        official_symbol="TMPV",
        relation_type="SEPARATE_SECURITY",
    )
    path = _write_ledger(tmp_path, [row])
    report = audit_security_aliases(path)
    assert report["ready"] is False
    assert any("must retain its own symbol" in error for error in report["errors"])


def test_overlapping_alias_intervals_cannot_map_to_different_securities(tmp_path):
    first = _verified_row(tmp_path, alias_id="A1", valid_from="2024-01-01", valid_to="2025-01-01")
    second = _verified_row(
        tmp_path,
        alias_id="A2",
        official_symbol="OTHER",
        security_id="INE999A01007",
        valid_from="2024-06-01",
    )
    path = _write_ledger(tmp_path, [first, second])
    report = audit_security_aliases(path)
    assert report["ready"] is False
    assert any("multiple official symbols" in error for error in report["errors"])


def test_bad_source_digest_blocks_verified_alias(tmp_path):
    row = _verified_row(tmp_path, source_sha256="0" * 64)
    path = _write_ledger(tmp_path, [row])
    report = audit_security_aliases(path)
    assert report["ready"] is False
    assert any("SHA-256 mismatch" in error for error in report["errors"])


def test_invalid_isin_blocks_verified_alias(tmp_path):
    row = _verified_row(tmp_path, security_id="INE214T01010")
    path = _write_ledger(tmp_path, [row])
    report = audit_security_aliases(path)
    assert report["ready"] is False
    assert any("valid ISIN" in error for error in report["errors"])


def test_ltim_symbol_history_uses_official_2026_rename_not_a_2023_vendor_alias():
    root = Path(__file__).resolve().parents[1]
    with (root / "data" / "reference" / "security_symbol_aliases.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    row = next(item for item in rows if item["alias_id"] == "ALIAS-LTIM-LTM-NSE-RENAME-2026")
    assert row["alias_symbol"] == "LTIM"
    assert row["official_symbol"] == "LTM"
    assert row["relation_type"] == "TICKER_RENAME_SAME_SECURITY"
    assert row["valid_from"] == "2026-02-27"
    assert row["valid_to"] == ""
    assert row["security_id"] == "INE214T01019"
    assert row["source_url"].endswith("/CML72948.pdf")
    assert row["verification_status"] == "UNVERIFIED"


def test_historical_nifty50_ltim_events_keep_the_official_ltim_symbol():
    root = Path(__file__).resolve().parents[1]
    with (root / "data" / "reference" / "nifty50_transition_register.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    ltim_rows = [row for row in rows if row["transition_id"] in {
        "N50-2023-LTIM-IN", "N50-2024-LTIM-OUT"
    }]
    assert len(ltim_rows) == 2
    assert {row["symbol"] for row in ltim_rows} == {"LTIM"}


def test_verified_alias_requires_independent_reviewer_signoff(tmp_path):
    row = _verified_row(tmp_path, reviewer="", reviewed_at="")
    path = _write_ledger(tmp_path, [row])
    report = audit_security_aliases(path)
    assert report["ready"] is False
    assert any("independent reviewer sign-off" in error for error in report["errors"])


def test_verified_alias_rejects_invalid_review_date(tmp_path):
    row = _verified_row(tmp_path, reviewed_at="not-a-date")
    path = _write_ledger(tmp_path, [row])
    report = audit_security_aliases(path)
    assert report["ready"] is False
    assert any("reviewed_at must be an ISO calendar date" in error for error in report["errors"])


def test_tata_motors_rename_and_tmcvl_listing_keep_distinct_security_ids():
    root = Path(__file__).resolve().parents[1]
    with (root / "data" / "reference" / "security_symbol_aliases.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    rename = next(item for item in rows if item["alias_id"] == "ALIAS-TATAMOTORS-TMPV")
    separate = next(item for item in rows if item["alias_id"] == "ENTITY-TMCV-SEPARATE")
    assert (rename["alias_symbol"], rename["official_symbol"]) == ("TATAMOTORS", "TMPV")
    assert rename["security_id"] == "INE155A01022"
    assert rename["valid_from"] == "2025-10-24"
    assert rename["verification_status"] == "UNVERIFIED"
    assert separate["alias_symbol"] == separate["official_symbol"] == "TMCV"
    assert separate["relation_type"] == "SEPARATE_SECURITY"
    assert separate["security_id"] == "INE1TAE01010"
    assert separate["valid_from"] == "2025-11-12"
    assert separate["security_id"] != rename["security_id"]
    assert separate["verification_status"] == "UNVERIFIED"
