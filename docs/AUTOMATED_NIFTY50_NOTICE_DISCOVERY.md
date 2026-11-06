# Automated Nifty 50 notice discovery

## Objective

The research pipeline, not a manually curated checklist, discovers NSE Indices press-release archive entries for the point-in-time universe window (2018-04-01 through 2024-12-31).

## Automation

- Workflow: `.github/workflows/discover-nifty50-notices.yml`
- Implementation: `trader/nifty_notice_discovery.py`
- Tests: `tests/test_nifty_notice_discovery.py` and `tests/test_nifty_notice_screening.py`
- Text screening: `trader/nifty_notice_screening.py`
- Text-screening report: `data/reports/nifty50_notice_text_screening.json`
- Source archive: https://www.niftyindices.com/press-release
- Review-candidate inventory: `data/reference/nifty50_annual_notice_inventory.csv`
- Complete archive catalog: `data/reference/nifty50_archive_discovery_catalog.csv`
- Discovery report: `data/reports/nifty50_notice_discovery.json`
- Archived primary PDFs: `data/reference/source_documents/`

The workflow runs monthly and can also be started manually. It parses **all** archive entries in the requested date window, deduplicates by canonical source URL, and persists every entry (including non-candidates) in the complete archive catalog. A separate review-candidate inventory drives PDF downloads. The pipeline then extracts text from archived PDFs and reports exact Nifty 50 references with surrounding snippets, page counts, text lengths, and source-hash checks. It retains publication dates and titles, and downloads candidate primary PDFs from approved NSE Indices hosts. Each archived PDF receives a SHA-256 hash calculated from the downloaded bytes.

## Safety and evidence policy

1. Every archive entry is retained in the complete catalog with `UNREVIEWED` scope status; candidate inventory rows start as `UNCLASSIFIED_REVIEW_REQUIRED` and `DISCOVERED_UNREVIEWED`.
2. Title-keyword matching and PDF text matching are triage only. A mention or absence of the exact phrase is not a Nifty 50 scope decision.
3. The discovery job never creates constituent intervals, never changes a row to `VERIFIED`, and never marks annual coverage complete.
4. Existing human classifications and notice IDs are preserved.
5. URL hosts and redirects are allow-listed; downloads must be HTTPS PDFs and are size-limited.
6. Discovery and archiving success do not prove that the annual archive or ad-hoc circular inventory is complete.
7. PDF text interpretation, supersession/deferment analysis, historical snapshot reconciliation, and independent review remain separate gates.

## Acceptance

A successful workflow run means the archive was reachable and candidate entries were processed. It does **not** mean the Nifty 50 coverage gate passed. Coverage remains blocked until every candidate is screened, the ad-hoc exchange circular inventory is reconciled, transition events are independently verified, historical constituent snapshots agree, and the full interval ledger passes the fail-closed audit.

The workflow must never promote the model or unlock the confirmatory holdout.
