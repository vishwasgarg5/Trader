from pathlib import Path

from trader.nifty50_price_data_readiness import _audit_rows, audit_price_data_readiness


def test_current_repository_fails_closed_without_price_or_tri_observations():
    root = Path(__file__).resolve().parents[1] / "data" / "reference"
    report = audit_price_data_readiness(root)
    assert report["ready_for_price_and_benchmark_research"] is False
    assert report["ohlcv_rows"] == 0
    assert report["tri_rows"] == 0
    assert report["membership_prerequisite_ready"] is False
    assert report["security_identity_prerequisite_ready"] is False
    assert report["corporate_action_adjustment_verified"] is False
    assert any("no verified historical observations" in error for error in report["errors"])
    assert any("Step 2 prerequisite blocked" in error for error in report["errors"])
    assert any("Step 3 prerequisite blocked" in error for error in report["errors"])


def test_ohlcv_and_tri_contract_files_are_header_only_not_synthetic_data():
    root = Path(__file__).resolve().parents[1] / "data" / "reference"
    for name in ("nifty50_pilot_ohlcv.csv", "nifty50_tri.csv"):
        lines = (root / name).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1


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
