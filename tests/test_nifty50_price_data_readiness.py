from pathlib import Path
import csv

from trader.nifty50_price_data_readiness import _audit_rows, audit_price_data_readiness


def test_current_repository_fails_closed_without_verified_ohlcv_and_prerequisites():
    root = Path(__file__).resolve().parents[1] / "data" / "reference"
    report = audit_price_data_readiness(root)
    assert report["ready_for_price_and_benchmark_research"] is False
    assert report["ohlcv_rows"] == 0
    # TRI has been acquired, but acquisition is not independent verification.
    assert report["tri_rows"] > 0
    assert report["membership_prerequisite_ready"] is False
    assert report["security_identity_prerequisite_ready"] is False
    assert report["corporate_action_adjustment_verified"] is False
    assert any(
        "nifty50_pilot_ohlcv.csv: no verified historical observations" in error
        for error in report["errors"]
    )
    assert any("Step 2 prerequisite blocked" in error for error in report["errors"])
    assert any("Step 3 prerequisite blocked" in error for error in report["errors"])


def test_ohlcv_remains_header_only_while_acquired_tri_is_pending_review():
    root = Path(__file__).resolve().parents[1] / "data" / "reference"
    ohlcv_lines = (root / "nifty50_pilot_ohlcv.csv").read_text(encoding="utf-8").splitlines()
    assert len(ohlcv_lines) == 1

    with (root / "nifty50_tri.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert {
            "session_date", "tri_close", "source_url", "evidence_path",
            "evidence_sha256", "verification_status", "reviewer", "reviewed_at",
        }.issubset(set(reader.fieldnames or []))
    assert rows
    assert all(row["verification_status"] == "ACQUIRED_PENDING_INDEPENDENT_REVIEW" for row in rows)
    assert all(not row["reviewer"] and not row["reviewed_at"] for row in rows)


def _valid_ohlcv_row(**overrides):
    row = {
        "security_id": "INE009A01021",
        "symbol": "INFY",
        "session_date": "2026-01-02",
        "open": "100",
        "high": "105",
        "low": "99",
        "close": "103",
        "volume": "1000",
        "adjusted_close": "103",
        "source_url": "https://example.com/source.csv",
        "source_published_at": "2026-01-02",
        "evidence_path": "evidence/source.csv",
        "evidence_sha256": "a" * 64,
        "verification_status": "VERIFIED",
        "reviewer": "independent-reviewer",
        "reviewed_at": "2026-01-03",
    }
    row.update(overrides)
    return row


def test_ohlcv_requires_valid_isin_not_merely_nonblank_security_id():
    errors = _audit_rows(
        Path("nifty50_pilot_ohlcv.csv"),
        [_valid_ohlcv_row(security_id="NOT-AN-ISIN")],
        tri=False,
    )
    assert any("security_id must be a valid ISIN" in error for error in errors)


def test_ohlcv_accepts_valid_isin_shape_and_check_digit():
    errors = _audit_rows(
        Path("nifty50_pilot_ohlcv.csv"),
        [_valid_ohlcv_row()],
        tri=False,
    )
    assert not any("security_id" in error for error in errors)



def test_price_rows_reject_evidence_path_outside_evidence_root(tmp_path):
    outside = tmp_path / "outside.csv"
    outside.write_text("source", encoding="utf-8")
    row = _valid_ohlcv_row(
        evidence_path="../outside.csv",
        evidence_sha256=__import__("hashlib").sha256(outside.read_bytes()).hexdigest(),
    )

    errors = _audit_rows(
        Path("nifty50_pilot_ohlcv.csv"),
        [row],
        tri=False,
        evidence_root=tmp_path / "reference",
    )

    assert any("must stay inside the evidence root" in error for error in errors)


def test_price_rows_verify_archived_evidence_checksum(tmp_path):
    import hashlib

    evidence_root = tmp_path / "repo"
    evidence = evidence_root / "data" / "reference" / "evidence" / "source.csv"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("source bytes", encoding="utf-8")
    row = _valid_ohlcv_row(
        evidence_path="data/reference/evidence/source.csv",
        evidence_sha256=hashlib.sha256(b"different bytes").hexdigest(),
    )

    errors = _audit_rows(
        Path("nifty50_pilot_ohlcv.csv"),
        [row],
        tri=False,
        evidence_root=evidence_root,
    )

    assert any("archived evidence SHA-256 mismatch" in error for error in errors)
