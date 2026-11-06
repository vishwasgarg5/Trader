import hashlib

import pandas as pd

from trader.universe_audit import apply_point_in_time_membership, audit_universe


def _audited_membership(tmp_path, rows):
    path = tmp_path / "universe_membership.csv"
    evidence = tmp_path / "nse-source.pdf"
    evidence.write_bytes(b"archived official-source fixture")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    records = []
    for symbol, valid_from, valid_to in rows:
        records.append({
            "symbol": symbol,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "source": "NSE Indices circular fixture",
            "source_url": "https://www.nseindia.com/",
            "source_published_at": "2019-12-20T09:00:00+05:30",
            "evidence_path": evidence.name,
            "evidence_sha256": digest,
        })
    pd.DataFrame(records).to_csv(path, index=False)
    prices = pd.DataFrame(
        {"open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5], "volume": [100]},
        index=pd.DatetimeIndex(["2020-01-02"]),
    )
    report = audit_universe({"AAA.NS": prices, "^NSEI": prices}, ["AAA.NS"], path)
    return path, report


def test_half_open_interval_includes_valid_from_and_excludes_valid_to(tmp_path):
    path, report = _audited_membership(tmp_path, [("AAA.NS", "2020-01-02", "2020-01-04")])
    assert report["membership_history"]["valid"] is True
    dates = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"])
    frame = pd.DataFrame({"symbol": ["AAA.NS"] * 4, "target": [0, 1, 0, 1]}, index=dates)

    filtered, metadata = apply_point_in_time_membership(frame, path, report)

    assert metadata["applied"] is True
    assert filtered.index.strftime("%Y-%m-%d").tolist() == ["2020-01-02", "2020-01-03"]


def test_future_membership_interval_does_not_make_earlier_rows_eligible(tmp_path):
    path, report = _audited_membership(tmp_path, [("AAA.NS", "2020-01-04", "")])
    frame = pd.DataFrame(
        {"symbol": ["AAA.NS"] * 4, "target": [0, 1, 0, 1]},
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]),
    )

    filtered, _ = apply_point_in_time_membership(frame, path, report)

    assert filtered.index.strftime("%Y-%m-%d").tolist() == ["2020-01-04"]


def test_zero_length_half_open_interval_is_rejected(tmp_path):
    path, report = _audited_membership(tmp_path, [("AAA.NS", "2020-01-04", "2020-01-04")])
    assert report["membership_history"]["valid"] is False
    assert any("precedes" in error for error in report["membership_history"]["errors"])
