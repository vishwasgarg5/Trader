import csv
import hashlib

import pytest

from scripts.build_nse_bhavcopy_calendar_manifest import build_manifest


def test_manifest_builder_keeps_exact_tri_dates_and_verifies_source_bytes(tmp_path, monkeypatch):
    import scripts.build_nse_bhavcopy_calendar_manifest as module
    source = tmp_path / "tri-halfyear.json"
    source.write_text('{"rows":[]}', encoding="utf-8")
    tri = tmp_path / "tri.csv"
    with tri.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "session_date", "source_url", "evidence_path", "evidence_sha256", "verification_status"
        ])
        writer.writeheader()
        writer.writerow({
            "session_date": "2024-07-06",
            "source_url": "https://niftyindices.com/BackPage/getTotalReturnIndexString",
            "evidence_path": "tri-halfyear.json",
            "evidence_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "verification_status": "ACQUIRED_PENDING_INDEPENDENT_REVIEW",
        })
    monkeypatch.setattr(module, "ROOT", tmp_path)
    rows = build_manifest(tri, {"2024-07-06"})
    assert rows[0]["trade_date"] == "2024-07-06"
    assert rows[0]["calendar_review_status"] == "CANDIDATE_UNREVIEWED_TRI_OBSERVATION"
    assert rows[0]["tri_verification_status"] == "ACQUIRED_PENDING_INDEPENDENT_REVIEW"


def test_manifest_builder_rejects_missing_requested_date(tmp_path, monkeypatch):
    import scripts.build_nse_bhavcopy_calendar_manifest as module
    source = tmp_path / "tri.json"
    source.write_text("{}", encoding="utf-8")
    tri = tmp_path / "tri.csv"
    tri.write_text(
        "session_date,source_url,evidence_path,evidence_sha256,verification_status\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="requested dates missing"):
        build_manifest(tri, {"2024-07-08"})
