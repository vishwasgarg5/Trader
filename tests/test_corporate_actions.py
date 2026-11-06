import hashlib

import pandas as pd

from trader.corporate_actions import audit_corporate_action_ledger


def _ledger(path, evidence, digest):
    pd.DataFrame([{
        "symbol": "AAA.NS",
        "ex_date": "2024-01-10",
        "action_type": "split",
        "adjustment_factor": 0.5,
        "source": "NSE corporate action circular",
        "source_url": "https://www.nseindia.com/",
        "source_published_at": "2024-01-02T10:00:00+05:30",
        "evidence_path": evidence.name,
        "evidence_sha256": digest,
    }]).to_csv(path, index=False)


def test_corporate_action_ledger_requires_archived_source_evidence(tmp_path):
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"official action terms")
    path = tmp_path / "corporate_actions.csv"
    _ledger(path, evidence, hashlib.sha256(evidence.read_bytes()).hexdigest())
    result = audit_corporate_action_ledger(path)
    assert result["valid"] is True
    assert result["status"] == "evidence_valid_unverified_adjustment"
    assert result["corporate_action_adjustment_verified"] is False


def test_corporate_action_ledger_rejects_bad_checksum(tmp_path):
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"changed action terms")
    path = tmp_path / "corporate_actions.csv"
    _ledger(path, evidence, "0" * 64)
    result = audit_corporate_action_ledger(path)
    assert result["valid"] is False
    assert any("checksum mismatch" in error for error in result["errors"])


def test_corporate_action_ledger_rejects_nonfinite_factors_and_lookahead(tmp_path):
    evidence = tmp_path / "circular.pdf"
    evidence.write_bytes(b"action")
    path = tmp_path / "corporate_actions.csv"
    pd.DataFrame([{
        "symbol": "AAA.NS", "ex_date": "2024-01-10", "action_type": "split",
        "adjustment_factor": float("inf"), "source": "NSE circular",
        "source_url": "https://www.nseindia.com/",
        "source_published_at": "2024-01-11T10:00:00+05:30",
        "evidence_path": evidence.name,
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }]).to_csv(path, index=False)
    result = audit_corporate_action_ledger(path)
    assert result["valid"] is False
    assert any("finite and positive" in error for error in result["errors"])
    assert any("after the corporate action ex_date" in error for error in result["errors"])


def test_naive_late_evening_ex_date_keeps_nse_calendar_date():
    from trader.corporate_actions import _india_calendar_dates

    values = pd.Series(["2024-01-10 23:45:00", "2024-01-10T18:30:00Z"])
    dates = _india_calendar_dates(values)
    assert dates.dt.strftime("%Y-%m-%d").tolist() == ["2024-01-10", "2024-01-11"]


def test_committed_tata_motors_source_notes_are_integrity_valid_but_not_price_verified():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = audit_corporate_action_ledger(root / "data" / "reference" / "corporate_actions.csv")
    assert result["valid"] is True
    assert result["status"] == "evidence_valid_unverified_adjustment"
    assert result["corporate_action_adjustment_verified"] is False


def test_missing_adjustment_factor_is_explicitly_unresolved_not_assumed_neutral(tmp_path):
    evidence = tmp_path / "demerger-note.txt"
    evidence.write_text("official filing summary; not a price adjustment factor", encoding="utf-8")
    path = tmp_path / "corporate_actions.csv"
    pd.DataFrame([{
        "symbol": "AAA.NS", "ex_date": "2024-01-10",
        "action_type": "demerger_price_discovery",
        "adjustment_factor": None, "source": "Company filing summary",
        "source_url": "https://www.nseindia.com/",
        "source_published_at": "2024-01-02T10:00:00+05:30",
        "evidence_path": evidence.name,
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }]).to_csv(path, index=False)
    result = audit_corporate_action_ledger(path)
    assert result["valid"] is True
    assert result["unresolved_adjustment_factor_rows"] == 1
    assert result["corporate_action_adjustment_verified"] is False
