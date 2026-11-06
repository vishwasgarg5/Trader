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
            f"{year},{year}-01-01,{year}-12-31,false,,,,,,,NOT_STARTED,"
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
