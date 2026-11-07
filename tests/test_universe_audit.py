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


def test_audit_flags_missing_ohlcv_columns(tmp_path):
    prices = _prices()
    prices["AAA.NS"] = prices["AAA.NS"].drop(columns=["volume"])
    report = audit_universe(prices, ["AAA.NS"], tmp_path / "none.csv")
    assert report["per_symbol"]["AAA.NS"]["missing_ohlcv_columns"] == ["volume"]
    assert "AAA.NS" in report["price_integrity_issues"]


def test_audit_normalizes_aware_price_and_benchmark_indices_to_nse_date(tmp_path):
    index = pd.DatetimeIndex([pd.Timestamp("2024-01-10T18:30:00Z")])
    bars = pd.DataFrame(
        {"open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5], "volume": [1000]},
        index=index,
    )
    benchmark = pd.DataFrame({"close": [21000.0]}, index=index)
    report = audit_universe(
        {"AAA.NS": bars, "^NSEI": benchmark},
        ["AAA.NS"],
        tmp_path / "no-membership.csv",
    )
    row = report["per_symbol"]["AAA.NS"]
    assert row["last_date"] == "2024-01-11"
    assert row["missing_benchmark_sessions"] == 0


def test_audit_flags_non_finite_ohlcv_values(tmp_path):
    prices = _prices()
    prices["AAA.NS"].loc[prices["AAA.NS"].index[0], "close"] = float("inf")
    report = audit_universe(prices, ["AAA.NS"], tmp_path / "missing-membership.csv")
    assert report["per_symbol"]["AAA.NS"]["invalid_ohlc_rows"] == 1
    assert "AAA.NS" in report["price_integrity_issues"]



def test_membership_history_must_cover_every_configured_symbol(tmp_path):
    path = tmp_path / "universe_membership.csv"
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"official evidence fixture")
    pd.DataFrame([{
        "symbol": "AAA.NS", "valid_from": "2020-01-01", "valid_to": "",
        "source": "NSE circular", "source_url": "https://www.nseindia.com/",
        "source_published_at": "2019-12-20T09:00:00+05:30",
        "evidence_path": evidence.name,
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }]).to_csv(path, index=False)
    report = audit_universe(_prices(), ["AAA.NS", "BBB.NS"], path)
    assert report["membership_history"]["valid"] is False
    assert any("BBB.NS" in error for error in report["membership_history"]["errors"])


def test_membership_history_allows_former_constituents_outside_current_universe(tmp_path):
    path = tmp_path / "universe_membership.csv"
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"official evidence fixture")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    pd.DataFrame([
        {
            "symbol": "AAA.NS", "valid_from": "2020-01-01", "valid_to": "",
            "source": "NSE circular", "source_url": "https://www.nseindia.com/",
            "source_published_at": "2019-12-20T09:00:00+05:30",
            "evidence_path": evidence.name, "evidence_sha256": digest,
        },
        {
            "symbol": "FORMER.NS", "valid_from": "2018-01-01", "valid_to": "2020-01-01",
            "source": "NSE circular", "source_url": "https://www.nseindia.com/",
            "source_published_at": "2017-12-20T09:00:00+05:30",
            "evidence_path": evidence.name, "evidence_sha256": digest,
        },
    ]).to_csv(path, index=False)
    report = audit_universe(_prices(), ["AAA.NS"], path)
    assert report["membership_history"]["valid"] is True
    assert report["membership_history"]["rows"] == 2
    assert report["point_in_time_universe_verified"] is False


def test_membership_evidence_path_cannot_escape_membership_directory(tmp_path):
    path = tmp_path / "universe_membership.csv"
    outside = tmp_path.parent / "outside-evidence.bin"
    outside.write_bytes(b"outside evidence must not be accepted")
    pd.DataFrame([{
        "symbol": "AAA.NS", "valid_from": "2020-01-01", "valid_to": "",
        "source": "NSE circular", "source_url": "https://www.nseindia.com/",
        "source_published_at": "2019-12-20T09:00:00+05:30",
        "evidence_path": "../outside-evidence.bin",
        "evidence_sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
    }]).to_csv(path, index=False)
    report = audit_universe(_prices(), ["AAA.NS"], path)
    assert report["membership_history"]["valid"] is False
    assert any("escapes membership directory" in item for item in report["membership_history"]["errors"])
