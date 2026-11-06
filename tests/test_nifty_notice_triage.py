from pathlib import Path

from trader.nifty_notice_triage import classify_title, run


def test_title_triage_separates_constituent_changes_from_other_indices():
    assert classify_title("Changes in Indices w.e.f. April 02, 2018") == "PRIORITY_CONSTITUENT_CHANGE_REVIEW"
    assert classify_title("Replacements in Fixed income Indices") == "LOW_PRIORITY_LIKELY_OTHER_INDEX"
    assert classify_title("Change in NIFTY 10 Year SDL Index") == "LOW_PRIORITY_LIKELY_OTHER_INDEX"
    assert classify_title("Nifty 50 constituent replacement") == "PRIORITY_CONSTITUENT_CHANGE_REVIEW"


def test_triage_never_marks_review_complete_or_membership(tmp_path):
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(
        "notice_id,announcement_date,notes,source_url,source_document_path,source_sha256,review_status\n"
        "n1,2018-01-01,Archive title: Changes in Indices,https://example.test/a,, ,DISCOVERED_UNREVIEWED\n",
        encoding="utf-8",
    )
    report = run(inventory, tmp_path / "report.json", tmp_path / "events.csv")
    assert report["coverage_complete"] is False
    assert report["membership_written"] is False
    assert report["triage"][0]["review_status_unchanged"] == "DISCOVERED_UNREVIEWED"
    assert report["triage"][0]["text_extraction_status"] == "MISSING_SOURCE_DOCUMENT"
