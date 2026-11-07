import csv

from trader.nifty50_notice_triage import build_triage, classify


def test_classify_is_conservative_and_never_signs_off():
    category, _ = classify({
        "observed_nifty50_effect": "UNCLASSIFIED_REVIEW_REQUIRED",
        "review_status": "DISCOVERED_UNREVIEWED",
    })
    assert category == "UNRESOLVED_REVIEW_REQUIRED"

    category, _ = classify({
        "observed_nifty50_effect": "NO_FLAGSHIP_NIFTY50_CONSTITUENT_CHANGE",
        "review_status": "SCREENED_NO_NIFTY50_CHANGE",
    })
    assert category == "OUT_OF_SCOPE_CANDIDATE_HUMAN_SIGNOFF"

    category, _ = classify({
        "observed_nifty50_effect": "Accelerated YESBANK removal and SHREECEM addition",
        "review_status": "CANDIDATE",
    })
    assert category == "MEMBERSHIP_OR_EFFECTIVE_DATE_REVIEW"


def test_build_triage_writes_review_queue_without_changing_membership(tmp_path):
    source = tmp_path / "inventory.csv"
    details = tmp_path / "triage.csv"
    summary_path = tmp_path / "triage.json"
    fields = [
        "notice_id", "year", "announcement_date", "effective_date", "source_role",
        "source_url", "observed_nifty50_effect", "source_document_path",
        "source_sha256", "review_status", "notes",
    ]
    rows = [
        {
            "notice_id": "a", "year": "2020", "announcement_date": "2020-03-16",
            "effective_date": "2020-03-19", "source_role": "NOTICE",
            "source_url": "https://example.test/a.pdf",
            "observed_nifty50_effect": "Accelerated YESBANK removal and SHREECEM addition",
            "source_document_path": "docs/a.pdf", "source_sha256": "abc",
            "review_status": "CANDIDATE", "notes": "manual chain review",
        },
        {
            "notice_id": "b", "year": "2020", "announcement_date": "2020-03-20",
            "effective_date": "", "source_role": "ARCHIVE",
            "source_url": "https://example.test/b.pdf",
            "observed_nifty50_effect": "UNCLASSIFIED_REVIEW_REQUIRED",
            "source_document_path": "", "source_sha256": "",
            "review_status": "DISCOVERED_UNREVIEWED", "notes": "",
        },
    ]
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = build_triage(source, details, summary_path)
    assert summary["inventory_rows"] == 2
    assert summary["membership_written"] is False
    assert summary["source_rows_modified"] is False
    assert summary["human_signoff_required_for_every_row"] is True
    assert summary["triage_category_counts"] == {
        "MEMBERSHIP_OR_EFFECTIVE_DATE_REVIEW": 1,
        "UNRESOLVED_REVIEW_REQUIRED": 1,
    }
    with details.open(newline="", encoding="utf-8") as handle:
        result = list(csv.DictReader(handle))
    assert all(row["human_review_required"] == "true" for row in result)
    assert all(row["human_signoff_status"] == "PENDING" for row in result)
    assert result[0]["source_sha256"] == "abc"
