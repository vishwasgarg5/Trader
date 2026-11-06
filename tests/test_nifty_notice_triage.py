from pathlib import Path
import hashlib

from pypdf import PdfWriter
import trader.nifty_notice_triage as triage

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



def test_scanned_notice_uses_ocr_and_records_source_and_text_hashes(tmp_path, monkeypatch):
    source = tmp_path / "scan.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with source.open("wb") as handle:
        writer.write(handle)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(
        triage, "_ocr_page_text",
        lambda path, page: ("NIFTY 50 constituents removed ABC and added XYZ w.e.f. 01 April 2021", "5.3.0"),
    )
    monkeypatch.setattr(triage, "OCR_TEXT_DIR", tmp_path / "ocr")
    events, status, metadata = triage._candidate_events(source, source_hash, "scan-1")
    assert status == "OCR_EXTRACTED"
    assert metadata["source_pdf_sha256"] == source_hash
    assert metadata["engine"] == "Tesseract"
    assert metadata["pages"] == [1]
    assert metadata["sha256"] == hashlib.sha256(
        (tmp_path / "ocr" / "scan-1.txt").read_bytes()
    ).hexdigest()
    assert events and events[0]["human_review_required"] is True
    assert events[0]["candidate_out_symbols"] == ""
    assert events[0]["candidate_in_symbols"] == ""



def test_triage_uses_canonical_archive_title_not_human_inventory_notes(tmp_path):
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(
        "notice_id,announcement_date,notes,source_url,source_document_path,source_sha256,review_status\n"
        "nifty50-2018,2018-02-21,Official release lists three removals and additions,"
        "https://www.niftyindices.com/Press_Release/ind_prs21022018.pdf,,,"
        "CANDIDATE\n",
        encoding="utf-8",
    )
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        "publication_date,title,source_url,review_candidate,scope_status,first_discovered_at_utc\n"
        "2018-02-21,Change in Indices w.e.f. April 02 2018,"
        "https://www.niftyindices.com/Press_Release/ind_prs21022018.pdf,true,UNREVIEWED,now\n",
        encoding="utf-8",
    )
    report = run(
        inventory, tmp_path / "report.json", tmp_path / "events.csv",
        catalog_path=catalog,
    )
    row = report["triage"][0]
    assert row["title"] == "Change in Indices w.e.f. April 02 2018"
    assert row["title_triage"] == "PRIORITY_CONSTITUENT_CHANGE_REVIEW"
    assert row["review_status_unchanged"] == "CANDIDATE"
    assert report["membership_written"] is False



def test_missing_pdf_for_explicitly_other_index_is_not_nifty50_integrity_failure(tmp_path):
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(
        "notice_id,announcement_date,notes,source_url,source_document_path,source_sha256,review_status\n"
        "sdl-1,2018-06-05,Archive title: Change in NIFTY 10 Year SDL Index w.e.f. June 06 2018,"
        "https://example.test/sdl.pdf,,,DISCOVERED_UNREVIEWED\n",
        encoding="utf-8",
    )
    report = run(inventory, tmp_path / "report.json", tmp_path / "events.csv")
    row = report["triage"][0]
    assert row["title_triage"] == "LOW_PRIORITY_LIKELY_OTHER_INDEX"
    assert row["text_extraction_status"] == "OUT_OF_SCOPE_SOURCE_NOT_REQUIRED"
    assert report["source_integrity_failures"] == []
    assert report["out_of_scope_source_not_required"] == ["sdl-1"]
    assert report["membership_written"] is False
