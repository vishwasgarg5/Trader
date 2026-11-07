import csv
import hashlib

from trader.nifty_notice_reconciliation import normalize_url, reconcile


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_normalize_url_ignores_query_fragment_and_host_case():
    assert normalize_url("HTTPS://EXAMPLE.COM/a.pdf?utm_source=x#page=2") == "https://example.com/a.pdf"


def test_reconcile_matches_by_url_and_flags_register_only_and_missing_archive(tmp_path):
    source_dir = tmp_path / "docs"
    source_dir.mkdir()
    pdf = source_dir / "notice.pdf"
    pdf.write_bytes(b"%PDF-1.4 fixture")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()

    inventory = tmp_path / "inventory.csv"
    register = tmp_path / "register.csv"
    catalog = tmp_path / "catalog.csv"
    report_path = tmp_path / "report.json"
    details_path = tmp_path / "details.csv"

    write_csv(inventory, [
        "notice_id", "announcement_date", "source_url", "source_document_path",
        "source_sha256", "review_status",
    ], [{
        "notice_id": "archive-id", "announcement_date": "2024-01-01",
        "source_url": "https://example.test/notice.pdf", "source_document_path": "docs/notice.pdf",
        "source_sha256": digest, "review_status": "DISCOVERED_UNREVIEWED",
    }])
    write_csv(register, [
        "notice_id", "publication_date", "source_url", "source_document_path",
        "source_sha256", "review_status",
    ], [
        {
            "notice_id": "curated-id", "publication_date": "2024-01-01",
            "source_url": "https://EXAMPLE.test/notice.pdf?utm_source=test",
            "source_document_path": "docs/notice.pdf", "source_sha256": digest,
            "review_status": "ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW",
        },
        {
            "notice_id": "located-id", "publication_date": "2024-02-01",
            "source_url": "https://example.test/other.pdf", "source_document_path": "",
            "source_sha256": "", "review_status": "LOCATED_NOT_ARCHIVED",
        },
    ])
    write_csv(catalog, ["source_url"], [
        {"source_url": "https://example.test/notice.pdf"},
        {"source_url": "https://example.test/catalog-only.pdf"},
    ])

    report = reconcile(inventory, register, catalog, report_path, details_path, tmp_path)
    assert report["inventory_rows"] == 1
    assert report["register_rows"] == 2
    assert report["register_rows_matched_to_inventory"] == 1
    assert report["register_rows_without_inventory_match"] == 1
    assert report["inventory_only_rows"] == 0
    assert report["hash_status_counts"]["HASH_MATCH"] == 2
    assert any(x["issue_type"] == "LOCATED_BUT_NOT_ARCHIVED" for x in report["issues"])
    assert report["coverage_complete"] is False
    assert report["membership_written"] is False
    assert f"{report['inventory_rows']}-row annual inventory" in report["policy"]


def test_reconcile_keeps_inventory_only_as_candidates_not_false_missing_notices(tmp_path):
    inventory = tmp_path / "inventory.csv"
    register = tmp_path / "register.csv"
    report_path = tmp_path / "report.json"
    details_path = tmp_path / "details.csv"
    write_csv(inventory, [
        "notice_id", "announcement_date", "source_url", "source_document_path",
        "source_sha256", "review_status",
    ], [{
        "notice_id": "broad-candidate", "announcement_date": "2020-01-01",
        "source_url": "https://example.test/broad.pdf", "source_document_path": "",
        "source_sha256": "", "review_status": "DISCOVERED_UNREVIEWED",
    }])
    write_csv(register, [
        "notice_id", "publication_date", "source_url", "source_document_path",
        "source_sha256", "review_status",
    ], [])
    report = reconcile(inventory, register, None, report_path, details_path, tmp_path)
    assert report["inventory_only_rows"] == 1
    assert report["register_rows_without_inventory_match"] == 0
    assert report["coverage_complete"] is False


def test_ragged_csv_rows_are_reported_instead_of_crashing(tmp_path):
    inventory = tmp_path / "inventory.csv"
    register = tmp_path / "register.csv"
    report_path = tmp_path / "report.json"
    details_path = tmp_path / "details.csv"
    inventory.write_text(
        "notice_id,announcement_date,source_url,source_document_path,source_sha256,review_status\n"
        "row-1,2024-01-01,https://example.test/a.pdf,,,DISCOVERED_UNREVIEWED,unexpected-extra\n",
        encoding="utf-8",
    )
    write_csv(register, [
        "notice_id", "publication_date", "source_url", "source_document_path",
        "source_sha256", "review_status",
    ], [])
    report = reconcile(inventory, register, None, report_path, details_path, tmp_path)
    assert any(
        issue["issue_type"] == "CSV_EXTRA_COLUMNS"
        and issue["notice_id"] == "row-1"
        for issue in report["issues"]
    )
    assert report["coverage_complete"] is False

def test_2020_nifty50_acceleration_survives_later_rebalancing_deferment_chain():
    """Regression: later general deferments must not undo the Nifty 50's March 19 event."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    with (root / "data/reference/nifty50_transition_register.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        transitions = list(csv.DictReader(handle))
    march_events = {
        row["transition_id"]: row
        for row in transitions
        if row["transition_id"] in {
            "N50-2020-YESBANK-OUT",
            "N50-2020-SHREECEM-IN",
        }
    }
    assert set(march_events) == {
        "N50-2020-YESBANK-OUT",
        "N50-2020-SHREECEM-IN",
    }
    assert {row["effective_date"] for row in march_events.values()} == {"2020-03-19"}
    assert all(row["verification_status"] == "SAMPLE_ONLY" for row in march_events.values())
    assert all(row["has_superseding_notice"] == "true" for row in march_events.values())

    with (root / "data/reference/nifty50_notice_register.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        notices = {row["publication_date"]: row for row in csv.DictReader(handle)
                   if row["publication_date"] in {"2020-03-23", "2020-03-25", "2020-05-13"}}
    assert set(notices) == {"2020-03-23", "2020-03-25", "2020-05-13"}
    assert notices["2020-03-23"]["cancellation_or_deferral_status"] == "DEFERRED_UNTIL_FURTHER_NOTICE"
    assert notices["2020-03-25"]["supersedes_notice_id"] == "NSE_INDICES_PR_2020-03-23"
    assert notices["2020-05-13"]["cancellation_or_deferral_status"] == (
        "EXCEPT_NIFTY50_AND_NIFTY_BANK_ALREADY_REBALANCED_2020-03-19"
    )
    assert notices["2020-05-13"]["nifty50_scope_result"] == "NIFTY50_CONFIRMATION"

    notice_texts = {
        "2020-03-23": (root / "data/reference/extracted_notice_text/N50-NOTICE-2020-03-23.txt").read_text(encoding="utf-8"),
        "2020-03-25": (root / "data/reference/extracted_notice_text/N50-NOTICE-2020-03-25.txt").read_text(encoding="utf-8"),
        "2020-05-13": (root / "data/reference/extracted_notice_text/N50-NOTICE-2020-05-13.txt").read_text(encoding="utf-8"),
    }
    assert "defer the upcoming index rebalancing" in notice_texts["2020-03-23"]
    assert "defer the above changes" in notice_texts["2020-03-25"]
    assert "except replacements in NIFTY 50 and NIFTY Bank index" in notice_texts["2020-05-13"]


def test_strides_source_archive_mismatch_remains_blocked():
    """Do not classify a Strides URL from the same-date Nifty IPO PDF extraction."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    notice_text = (root / "data/reference/extracted_notice_text/"
                   "NSE-ARCHIVE-2024-12-02-295b1f169428.txt").read_text(encoding="utf-8")
    assert "Replacement in Nifty IPO index" in notice_text
    assert "Corporate Adjustment for Strides Pharma Science Ltd." not in notice_text

    with (root / "data/reference/nifty50_archive_discovery_catalog.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    row = next(item for item in rows if item["source_url"].endswith("ind_prs02122024_1.pdf"))
    assert row["review_candidate"] == "false"
    assert row["scope_status"] == "SOURCE_ARCHIVE_IDENTITY_MISMATCH_BLOCKED"
