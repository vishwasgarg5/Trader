import csv

from trader.nifty50_pit_readiness import audit_pit_readiness


def _write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def test_repository_evidence_does_not_claim_pit_readiness():
    from trader.nifty50_pit_readiness import REFERENCE

    report = audit_pit_readiness(REFERENCE)
    assert report["ready_for_pit_research"] is False
    assert report["point_in_time_membership_verified"] is False
    assert report["membership_interval_rows"] == 0
    assert report["annual_coverage_incomplete_years"]
    assert report["errors"]
    # Counts evolve as new archive candidates are discovered; assert open blockers,
    # not stale snapshot totals. AI dispositions are not independent sign-off.
    assert report["unreviewed_archive_catalog_rows"] > 0
    assert report["unresolved_archive_catalog_rows"] > 0
    assert report["unresolved_annual_notice_rows"] > 0


def test_empty_membership_history_is_never_ready(tmp_path):
    ref = tmp_path / "reference"
    _write(ref / "nifty50_membership.csv", [
        "symbol", "issuer_name", "security_identifier", "valid_from", "valid_to",
        "notice_id", "source_url", "source_published_at", "evidence_path",
        "evidence_sha256", "verification_status", "reviewer", "reviewed_at", "notes",
    ], [])
    _write(ref / "nifty50_transition_register.csv", [
        "transition_id", "symbol", "action", "announcement_date", "effective_date",
        "source_url", "source_document_path", "source_sha256", "has_superseding_notice",
        "superseding_notice_url", "superseding_document_path", "superseding_sha256",
        "verification_status", "reviewer", "reviewed_at", "notes",
    ], [])
    _write(ref / "nifty50_annual_coverage.csv", [
        "year", "scope_start", "scope_end", "official_notice_search_complete",
        "expected_transition_count", "verified_transition_count",
        "supersession_review_complete", "snapshot_reconciliation_complete",
        "independent_reviewer", "reviewed_at", "coverage_status", "notes",
    ], [])
    _write(ref / "nifty50_special_membership_events.csv", [
        "event_id", "index_name", "member_key", "phase", "announcement_date",
        "effective_date", "constituent_count", "price_treatment", "source_url",
        "source_document_path", "source_sha256", "verification_status",
        "reviewer", "reviewed_at", "notes",
    ], [])
    _write(ref / "nifty50_archive_discovery_catalog.csv", [
        "publication_date", "title", "source_url", "review_candidate", "scope_status",
        "first_discovered_at_utc",
    ], [])
    _write(ref / "nifty50_annual_notice_inventory.csv", [
        "notice_id", "year", "announcement_date", "effective_date", "source_role",
        "source_url", "observed_nifty50_effect", "source_document_path",
        "source_sha256", "review_status", "notes",
    ], [])

    report = audit_pit_readiness(ref)
    assert report["ready_for_pit_research"] is False
    assert report["point_in_time_membership_verified"] is False
    assert any("no effective-dated membership intervals" in error for error in report["errors"])
