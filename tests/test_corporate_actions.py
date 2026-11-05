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
