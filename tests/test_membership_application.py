import hashlib

import pandas as pd
import pytest

from trader.universe_audit import apply_point_in_time_membership


def test_valid_membership_intervals_filter_research_rows_and_remain_unverified(tmp_path):
    evidence = tmp_path / "membership.pdf"
    evidence.write_bytes(b"official circular")
    path = tmp_path / "universe_membership.csv"
    pd.DataFrame([{
        "symbol": "AAA.NS", "valid_from": "2026-01-02", "valid_to": "2026-01-05",
        "source": "NSE Indices circular", "source_url": "https://www.niftyindices.com/press-release",
        "source_published_at": "2026-01-01T10:00:00+05:30",
        "evidence_path": evidence.name,
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }]).to_csv(path, index=False)
    frame = pd.DataFrame({
        "symbol": ["AAA.NS", "AAA.NS", "AAA.NS", "BBB.NS"],
        "feature": [1, 2, 3, 4],
    }, index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-06", "2026-01-03"]))
    audit = {"membership_history": {"valid": True, "errors": []}}
    filtered, status = apply_point_in_time_membership(frame, path, audit)
    assert len(filtered) == 1
    assert filtered.iloc[0]["feature"] == 2
    assert status["applied"] is True
    assert status["point_in_time_verified"] is False


def test_invalid_existing_membership_history_fails_closed(tmp_path):
    path = tmp_path / "universe_membership.csv"
    path.write_text("symbol,valid_from\nAAA.NS,2026-01-01\n")
    with pytest.raises(ValueError, match="invalid membership history"):
        apply_point_in_time_membership(
            pd.DataFrame({"symbol": ["AAA.NS"]}, index=pd.to_datetime(["2026-01-01"])),
            path, {"membership_history": {"valid": False, "errors": ["missing evidence"]}},
        )


def test_missing_membership_history_keeps_static_research_explicitly_unverified(tmp_path):
    frame = pd.DataFrame({"symbol": ["AAA.NS"]}, index=pd.to_datetime(["2026-01-01"]))
    filtered, status = apply_point_in_time_membership(
        frame, tmp_path / "missing.csv", {"membership_history": {"valid": False}},
    )
    assert len(filtered) == 1
    assert status["applied"] is False
    assert status["mode"] == "static_configured_unverified"
