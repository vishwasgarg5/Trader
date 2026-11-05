import hashlib

import pandas as pd

from trader.universe_audit import audit_universe


def _prices():
    idx = pd.bdate_range("2026-01-01", periods=3)
    bars = pd.DataFrame({
        "open": [10, 11, 12], "high": [11, 12, 13], "low": [9, 10, 11],
        "close": [10.5, 11.5, 12.5], "volume": [100, 0, 100],
    }, index=idx)
    return {"AAA.NS": bars, "^NSEI": pd.DataFrame({"close": [1, 2, 3]}, index=idx)}


def test_static_universe_is_never_claimed_point_in_time_verified(tmp_path):
    report = audit_universe(_prices(), ["AAA.NS", "MISSING.NS"], tmp_path / "none.csv")
    assert report["point_in_time_universe_verified"] is False
    assert report["membership_history"]["provided"] is False
    assert report["missing_symbols"] == ["MISSING.NS"]
    assert report["per_symbol"]["AAA.NS"]["zero_volume_rows"] == 1


def test_membership_file_requires_provenance_and_valid_dates(tmp_path):
    path = tmp_path / "universe_membership.csv"
    evidence = tmp_path / "nse-circular.pdf"
    evidence.write_bytes(b"archived official circular fixture")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    pd.DataFrame([{
        "symbol": "AAA.NS", "valid_from": "2020-01-01", "valid_to": "",
        "source": "NSE circular", "source_url": "https://www.nseindia.com/",
        "source_published_at": "2019-12-20T09:00:00+05:30", "evidence_path": evidence.name,
        "evidence_sha256": digest,
    }]).to_csv(path, index=False)
    report = audit_universe(_prices(), ["AAA.NS"], path)
    assert report["membership_history"]["valid"] is True
    # A supplied file is not automatically treated as independently authenticated.
    assert report["point_in_time_universe_verified"] is False


def test_invalid_membership_dates_are_rejected(tmp_path):
    path = tmp_path / "universe_membership.csv"
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"evidence")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    pd.DataFrame([{
        "symbol": "AAA.NS", "valid_from": "2021-01-01", "valid_to": "2020-01-01",
        "source": "NSE circular", "source_url": "https://www.nseindia.com/",
        "source_published_at": "2020-12-20T09:00:00+05:30", "evidence_path": evidence.name,
        "evidence_sha256": digest,
    }]).to_csv(path, index=False)
    report = audit_universe(_prices(), ["AAA.NS"], path)
    assert report["membership_history"]["valid"] is False
    assert any("precedes" in item for item in report["membership_history"]["errors"])



def test_audit_flags_symbols_stale_vs_latest_benchmark_session(tmp_path):
    prices = _prices()
    prices["AAA.NS"] = prices["AAA.NS"].iloc[:-1]
    report = audit_universe(prices, ["AAA.NS"], tmp_path / "none.csv")
    assert report["per_symbol"]["AAA.NS"]["stale_benchmark_sessions"] == 1
    assert "AAA.NS" in report["price_integrity_issues"]



def test_membership_evidence_checksum_mismatch_is_rejected(tmp_path):
    path = tmp_path / "universe_membership.csv"
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"original")
    pd.DataFrame([{
        "symbol": "AAA.NS", "valid_from": "2020-01-01", "valid_to": "",
        "source": "NSE circular", "source_url": "https://www.nseindia.com/",
        "source_published_at": "2019-12-20T09:00:00+05:30", "evidence_path": evidence.name,
        "evidence_sha256": "0" * 64,
    }]).to_csv(path, index=False)
    report = audit_universe(_prices(), ["AAA.NS"], path)
    assert report["membership_history"]["valid"] is False
    assert any("checksum mismatch" in item for item in report["membership_history"]["errors"])


def test_membership_source_published_after_effective_date_is_rejected(tmp_path):
    path = tmp_path / "universe_membership.csv"
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"late published evidence")
    pd.DataFrame([{
        "symbol": "AAA.NS", "valid_from": "2020-01-01", "valid_to": "",
        "source": "NSE circular", "source_url": "https://www.nseindia.com/",
        "source_published_at": "2020-01-02T09:00:00+05:30",
        "evidence_path": evidence.name,
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }]).to_csv(path, index=False)
    report = audit_universe(_prices(), ["AAA.NS"], path)
    assert report["membership_history"]["valid"] is False
    assert any("published after valid_from" in item for item in report["membership_history"]["errors"])


def test_naive_late_evening_membership_timestamp_keeps_nse_calendar_date():
    from trader.universe_audit import _india_calendar_dates

    values = pd.Series(["2024-01-10 23:45:00", "2024-01-10T18:30:00Z"])
    dates = _india_calendar_dates(values)
    assert dates.dt.strftime("%Y-%m-%d").tolist() == ["2024-01-10", "2024-01-11"]
