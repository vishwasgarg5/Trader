import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data/reference/nifty50_notice_register.csv"


def test_catalog_controls_are_registered_without_fabricating_archive_or_membership_evidence():
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = {row["notice_id"]: row for row in csv.DictReader(handle)}

    expected = {
        "NSE_INDICES_PR_2024-02-27_MEETING": (
            "https://www.niftyindices.com/Press_Release/ind_prs27022024.pdf",
            "CONTROL_ANNOUNCEMENT_ONLY",
        ),
        "NSE_INDICES_PR_2024-08-16_MEETING": (
            "https://www.niftyindices.com/Press_Release/ind_prs16082024.pdf",
            "CONTROL_ANNOUNCEMENT_ONLY",
        ),
        "NSE_INDICES_PR_2024-12-02_STRIDES_CA": (
            "https://www.niftyindices.com/Press_Release/ind_prs02122024_1.pdf",
            "OUT_OF_SCOPE_NIFTY50",
        ),
    }
    for notice_id, (url, scope) in expected.items():
        row = rows[notice_id]
        assert row["source_url"] == url
        assert row["nifty50_scope_result"] == scope
        assert row["review_status"] == "LOCATED_NOT_ARCHIVED"
        assert row["source_document_path"] == ""
        assert row["source_sha256"] == ""
        assert row["reviewer"] == ""
        assert row["reviewed_at"] == ""

    feb = rows["NSE_INDICES_PR_2024-02-27_MEETING"]
    aug = rows["NSE_INDICES_PR_2024-08-16_MEETING"]
    strides = rows["NSE_INDICES_PR_2024-12-02_STRIDES_CA"]
    assert feb["effective_date"] == ""
    assert "NSE_INDICES_PR_2024-02-28" in feb["notes"]
    assert aug["effective_date"] == ""
    assert "NSE_INDICES_PR_2024-08-23" in aug["notes"]
    assert strides["effective_date"] == "2024-12-06"
    assert "Nifty Microcap 250" in strides["notes"]
    assert "Nifty Total Market" in strides["notes"]
    assert "not an additional membership transition" in feb["notes"]
    assert "not an additional membership transition" in aug["notes"]
