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



def test_2018_05_24_multi_index_notice_is_not_a_flagship_nifty50_transition():
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = {row["notice_id"]: row for row in csv.DictReader(handle)}
    row = rows["NSE_INDICES_PR_2018-05-24_ind_prs24052018_pdf"]
    assert row["notice_type"] == "MULTI_INDEX_REVIEW_NO_NIFTY50_CHANGE"
    assert row["effective_date"] == "2018-06-29"
    assert row["nifty50_scope_result"] == "NO_CHANGE"
    assert row["review_status"] == "AI_REVIEWED_PENDING_HUMAN_SIGNOFF"
    assert row["source_document_path"].endswith("NOTICE-NSE-ARCHIVE-2018-05-24-51480acd46f7.pdf")
    assert row["source_sha256"] == "bbc4a4c04cae7a1ff924e8b3ef3f7acc6b3a9da069a1d6a36cfe0ae99189e957"
    assert "No flagship Nifty 50 constituent section" in row["notes"]
