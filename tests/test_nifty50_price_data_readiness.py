from pathlib import Path

from trader.nifty50_price_data_readiness import audit_price_data_readiness


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
