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

def test_2024_10_10_shariah_review_is_not_a_flagship_nifty50_transition():
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = {row["notice_id"]: row for row in csv.DictReader(handle)}
    row = rows["NSE_INDICES_PR_2024-10-10_ind_prs10102024_1_pdf"]
    assert row["notice_type"] == "SHARIAH_INDEX_MONTHLY_REVIEW_NO_FLAGSHIP_NIFTY50_CHANGE"
    assert row["publication_date"] == "2024-10-10"
    assert row["effective_date"] == "2024-10-31"
    assert row["nifty50_scope_result"] == "NO_CHANGE"
    assert row["review_status"] == "AI_REVIEWED_PENDING_HUMAN_SIGNOFF"
    assert row["source_document_path"].endswith("NOTICE-NSE-ARCHIVE-2024-10-10-6e38240ddbe2.pdf")
    assert row["source_sha256"] == "a24e99d89476f28d37954f5c818dbace7c6125d448ec050c1e0f949b6a0dd169"
    assert "15 exclusions and 5 inclusions in Nifty500 Shariah only" in row["notes"]
    assert "no change to Nifty50 Shariah and Nifty Shariah 25" in row["notes"]

def test_2018_06_20_ht_media_replacement_notice_is_not_a_flagship_nifty50_transition():
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = {row["notice_id"]: row for row in csv.DictReader(handle)}
    row = rows["NSE_INDICES_PR_2018-06-20_ind_prs20062018_pdf"]
    assert row["notice_type"] == "MULTI_INDEX_REPLACEMENT_NO_NIFTY50_CHANGE"
    assert row["publication_date"] == "2018-06-20"
    assert row["effective_date"] == "2018-06-29"
    assert row["nifty50_scope_result"] == "NO_CHANGE"
    assert row["review_status"] == "AI_REVIEWED_PENDING_HUMAN_SIGNOFF"
    assert row["source_document_path"].endswith("NOTICE-NSE-ARCHIVE-2018-06-20-93d360edf6a9.pdf")
    assert row["source_sha256"] == "e4853e8962fd4df7156f7d7077d3df3aba6ba354eb368a771036e3c7a6ec9385"
    assert "Nifty 500, Nifty Smallcap 250, Nifty MidSmallcap 400 and Nifty Media only" in row["notes"]
    assert "No flagship Nifty 50 constituent section or change" in row["notes"]


def test_2018_12_14_multi_index_replacement_notice_is_not_a_flagship_nifty50_transition():
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = {row["notice_id"]: row for row in csv.DictReader(handle)}
    row = rows["NSE_INDICES_PR_2018-12-14_ind_prs14122018_pdf"]
    assert row["notice_type"] == "MULTI_INDEX_REPLACEMENT_NO_NIFTY50_CHANGE"
    assert row["publication_date"] == "2018-12-14"
    assert row["effective_date"] == "2018-12-28"
    assert row["nifty50_scope_result"] == "NO_CHANGE"
    assert row["review_status"] == "AI_REVIEWED_PENDING_HUMAN_SIGNOFF"
    assert row["source_document_path"].endswith("NOTICE-NSE-ARCHIVE-2018-12-14-5cb490e8d50e.pdf")
    assert row["source_sha256"] == "0a9fb1a90d69d6d34c7893409ff33806ce153fd464b2ed7809ac132362c6afe0"
    assert "Nifty50 Value 20" in row["notes"]
    assert "No flagship Nifty 50 constituent section or change" in row["notes"]


def test_2019_01_21_dena_vijaya_replacement_notice_is_not_a_flagship_nifty50_transition():
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = {row["notice_id"]: row for row in csv.DictReader(handle)}
    row = rows["NSE_INDICES_PR_2019-01-21_ind_prs21012019_pdf"]
    assert row["notice_type"] == "MULTI_INDEX_REPLACEMENT_NO_NIFTY50_CHANGE"
    assert row["publication_date"] == "2019-01-21"
    assert row["effective_date"] == "2019-01-28"
    assert row["nifty50_scope_result"] == "NO_CHANGE"
    assert row["review_status"] == "AI_REVIEWED_PENDING_HUMAN_SIGNOFF"
    assert row["source_document_path"].endswith("NOTICE-NSE-ARCHIVE-2019-01-21-57963c247a09.pdf")
    assert row["source_sha256"] == "ff617ab210bc5a1519e2432ebc03a0737b2a103245b2cab0767442be7edd323d"
    assert "Nifty PSU Bank" in row["notes"]
    assert "No flagship Nifty 50 constituent section or change" in row["notes"]

def test_2019_04_08_excel_crop_replacement_notice_is_not_a_flagship_nifty50_transition():
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = {row["notice_id"]: row for row in csv.DictReader(handle)}
    row = rows["NSE_INDICES_PR_2019-04-08_ind_prs08042019_pdf"]
    assert row["notice_type"] == "MULTI_INDEX_REPLACEMENT_NO_NIFTY50_CHANGE"
    assert row["publication_date"] == "2019-04-08"
    assert row["effective_date"] == "2019-04-15"
    assert row["nifty50_scope_result"] == "NO_CHANGE"
    assert row["review_status"] == "AI_REVIEWED_PENDING_HUMAN_SIGNOFF"
    assert row["source_document_path"].endswith("NOTICE-NSE-ARCHIVE-2019-04-08-02ecb67eead3.pdf")
    assert row["source_sha256"] == "a4ff43189ea06cc6dbf53f3c5ac615b1b0c030fe0678c6fe38e991a5a05716af"
    assert "Nifty 500, Nifty Smallcap 250 and Nifty MidSmallcap 400 only" in row["notes"]
    assert row["affected_symbols"] == "EXCELCROP;SUNCLAYLTD"
    assert "No flagship Nifty 50 constituent section or change" in row["notes"]

