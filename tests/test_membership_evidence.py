from pathlib import Path

from trader.membership_evidence import audit_membership_evidence


def _write_inputs(tmp_path: Path, *, verified: bool = False):
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    transition = tmp_path / "transitions.csv"
    coverage = tmp_path / "coverage.csv"
    transition.write_text(
        "transition_id,symbol,action,announcement_date,effective_date,source_url,"
        "source_document_path,source_sha256,has_superseding_notice,"
        "superseding_notice_url,superseding_document_path,superseding_sha256,"
        "verification_status,reviewer,reviewed_at,notes\n"
        "E1,AAA,ADD,2018-05-01,2018-06-01,https://example.com/nse.pdf,"
        "nse.pdf,PLACEHOLDER,false,,,,SAMPLE_ONLY,,,fixture\n",
        encoding="utf-8",
    )
    rows = ["year,scope_start,scope_end,official_notice_search_complete,"
            "expected_transition_count,verified_transition_count,"
            "supersession_review_complete,snapshot_reconciliation_complete,"
            "independent_reviewer,reviewed_at,coverage_status,notes"]
    for year in range(2018, 2025):
        rows.append(
            f"{year},{'2018-04-01' if year == 2018 else f'{year}-01-01'},{year}-12-31,false,,,,,,,NOT_STARTED,"
        )
    coverage.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return transition, coverage, evidence_root


def test_sample_only_transition_and_unstarted_years_fail_closed(tmp_path):
    transition, coverage, evidence = _write_inputs(tmp_path)
    report = audit_membership_evidence(transition, coverage, evidence)
    assert report["ready"] is False
    assert any("not VERIFIED" in error for error in report["errors"])
    assert report["annual_years_complete"] == 0
    assert report["source_authenticity_independently_established"] is False


def test_missing_annual_coverage_rows_fail_closed(tmp_path):
    transition, coverage, evidence = _write_inputs(tmp_path)
    coverage.write_text(
        "\n".join(coverage.read_text(encoding="utf-8").splitlines()[:2]) + "\n",
        encoding="utf-8",
    )
    report = audit_membership_evidence(transition, coverage, evidence)
    assert report["ready"] is False
    assert any("annual coverage row is missing" in error for error in report["errors"])


def test_complete_year_requires_verified_events_and_hashed_primary_source(tmp_path):
    import csv
    import hashlib

    transition, coverage, evidence = _write_inputs(tmp_path)
    source = evidence / "nse.pdf"
    source.write_bytes(b"official circular fixture")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with transition.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "transition_id", "symbol", "action", "announcement_date", "effective_date",
            "source_url", "source_document_path", "source_sha256",
            "has_superseding_notice", "superseding_notice_url",
            "superseding_document_path", "superseding_sha256",
            "verification_status", "reviewer", "reviewed_at", "notes",
        ])
        writer.writerow([
            "E1", "AAA", "ADD", "2018-05-01", "2018-06-01",
            "https://example.com/nse.pdf", "nse.pdf", digest,
            "false", "", "", "", "VERIFIED", "independent-reviewer",
            "2026-11-06", "reviewed against archived source",
        ])
    with coverage.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "year", "scope_start", "scope_end", "official_notice_search_complete",
            "expected_transition_count", "verified_transition_count",
            "supersession_review_complete", "snapshot_reconciliation_complete",
            "independent_reviewer", "reviewed_at", "coverage_status", "notes",
        ])
        for year in range(2018, 2025):
            count = 1 if year == 2018 else 0
            writer.writerow([
                year, "2018-04-01" if year == 2018 else f"{year}-01-01", f"{year}-12-31", "true",
                count, count, "true", "true", "independent-reviewer",
                "2026-11-06", "COMPLETE", "annual search and snapshot reconciliation signed",
            ])
    report = audit_membership_evidence(transition, coverage, evidence)
    assert report["ready"] is True
    assert report["verified_transition_rows"] == 1
    assert report["annual_years_complete"] == 7



def test_transition_outside_research_scope_is_rejected(tmp_path):
    transition, coverage, evidence = _write_inputs(tmp_path)
    text = transition.read_text(encoding="utf-8").replace(
        "2018-06-01", "2017-12-31"
    )
    transition.write_text(text, encoding="utf-8")
    report = audit_membership_evidence(transition, coverage, evidence)
    assert report["ready"] is False
    assert any("outside the 2018-04-01 to 2024-12-31 scope" in error for error in report["errors"])


def test_annual_coverage_scope_must_match_the_defined_calendar_window(tmp_path):
    transition, coverage, evidence = _write_inputs(tmp_path)
    text = coverage.read_text(encoding="utf-8").replace(
        "2018,2018-04-01,2018-12-31", "2018,2018-01-01,2018-12-31"
    )
    coverage.write_text(text, encoding="utf-8")
    report = audit_membership_evidence(transition, coverage, evidence)
    assert report["ready"] is False
    assert any("scope must be 2018-04-01 through 2018-12-31" in error for error in report["errors"])
