from pathlib import Path
from trader.membership_evidence import audit_special_membership_events


def test_live_jiofin_special_event_ledger_is_present_but_not_promoted():
    root = Path(__file__).resolve().parents[1] / "data" / "reference"
    report = audit_special_membership_events(root / "nifty50_special_membership_events.csv")
    assert report["rows"] == 3
    assert report["ready"] is False
    assert report["verified_rows"] == 0
    assert any("not VERIFIED" in error for error in report["errors"])
