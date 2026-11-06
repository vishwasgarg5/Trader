import csv
import json

from trader.nifty_archive_catalog_audit import audit_catalog


def test_catalog_audit_surfaces_non_candidate_change_titles_without_classifying(tmp_path):
    catalog = tmp_path / "catalog.csv"
    report_path = tmp_path / "report.json"
    fields = [
        "publication_date", "title", "source_url", "review_candidate",
        "scope_status", "first_discovered_at_utc",
    ]
    with catalog.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "publication_date": "2024-01-01",
            "title": "Change in the Fixed Income Indices",
            "source_url": "https://www.niftyindices.com/example.pdf",
            "review_candidate": "false",
            "scope_status": "UNREVIEWED",
            "first_discovered_at_utc": "2026-01-01T00:00:00Z",
        })
        writer.writerow({
            "publication_date": "2024-02-01",
            "title": "IISL launches a new index",
            "source_url": "https://www.niftyindices.com/launch.pdf",
            "review_candidate": "false",
            "scope_status": "UNREVIEWED",
            "first_discovered_at_utc": "2026-01-01T00:00:00Z",
        })
        writer.writerow({
            "publication_date": "2024-03-01",
            "title": "Change in Nifty 50",
            "source_url": "https://www.niftyindices.com/nifty50.pdf",
            "review_candidate": "true",
            "scope_status": "UNREVIEWED",
            "first_discovered_at_utc": "2026-01-01T00:00:00Z",
        })

    report = audit_catalog(catalog, report_path)
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["catalog_rows_audited"] == 3
    assert report["potential_false_negatives_for_source_review"] == 1
    assert saved["potential_false_negatives"][0]["title_scope_hint"] == "NON_EQUITY_OR_SPECIALIZED_INDEX_HINT"
    assert saved["potential_false_negatives"][0]["decision"] == "SOURCE_CONTENT_REVIEW_REQUIRED"
    assert saved["coverage_complete"] is False
    assert "no membership interval" in saved["safety_policy"]


def test_explicit_nifty_sdl_titles_are_separated_from_equity_review_false_negatives(tmp_path):
    catalog = tmp_path / "catalog.csv"
    report_path = tmp_path / "report.json"
    fields = [
        "publication_date", "title", "source_url", "review_candidate",
        "scope_status", "first_discovered_at_utc",
    ]
    with catalog.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "publication_date": "2024-01-01",
            "title": "Change in NIFTY 10 Year SDL Index w.e.f. January 02, 2024",
            "source_url": "https://www.niftyindices.com/example.pdf",
            "review_candidate": "false",
            "scope_status": "UNREVIEWED",
            "first_discovered_at_utc": "2026-01-01T00:00:00Z",
        })
        writer.writerow({
            "publication_date": "2024-02-01",
            "title": "Changes in Indices w.e.f. February 29, 2024",
            "source_url": "https://www.niftyindices.com/equity.pdf",
            "review_candidate": "false",
            "scope_status": "UNREVIEWED",
            "first_discovered_at_utc": "2026-01-01T00:00:00Z",
        })

    report = audit_catalog(catalog, report_path)
    assert report["explicit_sdl_title_rows_separated"] == 1
    assert report["potential_false_negatives_for_source_review"] == 1
    assert report["explicit_sdl_title_rows"][0]["scope_status_unchanged"] == "UNREVIEWED"
    assert report["explicit_sdl_title_rows"][0]["decision"] == "TITLE_IDENTIFIES_SDL_INDEX_NOT_NIFTY50_EQUITY_CANDIDATE"
    assert report["potential_false_negatives"][0]["title"] == "Changes in Indices w.e.f. February 29, 2024"
    assert report["coverage_complete"] is False
