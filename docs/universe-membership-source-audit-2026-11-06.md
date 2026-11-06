# Universe membership source audit — 2026-11-06

## Decision

**Do not mark the configured universe point-in-time verified and do not apply this candidate dataset to backtests yet.** A useful independent reconstruction has been identified and cross-checked against the configured tickers, but its data semantics and provenance do not satisfy this repository's membership-evidence contract.

The current research gate remains HOLD. This audit is a source-discovery and compatibility result, not a promotion of membership evidence.

## Candidate source inspected

- Project: https://github.com/aditya-jha/nse-historical-membership
- Upstream commit inspected: `0786cd9159742f4f2012dcd5f01c1f224b0b019b` (2026-11-02).
- Candidate file: `index_history/data/index_membership_history.csv`
- Candidate file blob SHA: `4b762a75376b14b9db6304ef70237270bc8da397`
- Coverage report: https://github.com/aditya-jha/nse-historical-membership/blob/main/COVERAGE.md
- Dataset licence statement: CC0-1.0 for the repository's data files. The factual source material is attributed to public NSE Indices press releases and NSE circulars; the raw source documents are not redistributed in that dataset.
- The upstream README describes half-open membership intervals `[valid_from, valid_to)`. A blank `valid_to` denotes an open interval.

The upstream coverage report states that index-membership data runs through 2026-10-13. For Nifty 50, Nifty 100, Nifty 500, Nifty Next 50, Nifty Midcap 150 and Nifty Smallcap 250, it describes reliable coverage from 2018-04 onward, with best-effort earlier coverage. The same project explicitly documents historical reconstruction limitations: its 2026-11-02 validation report records 13/20 internal-consistency failures and 604/974 cardinality failures across its 41-index dataset. It reports 29/29 selected transition checks passing and 0/41 current-snapshot mismatches. These aggregate results are not a clean validation of every historical Nifty 50 interval.

## Comparison with this repository's configured universe

- `config/universe.txt` contains 49 configured tickers.
- All 49 ticker strings occur in at least one Nifty 50 interval in the candidate file.
- The candidate contains 84 Nifty 50 membership intervals in total.
- The configured 49 are **not** the complete historical Nifty 50 universe: the candidate contains other historical constituents that are absent from `config/universe.txt`.
- Therefore, the match proves only that each configured ticker appears somewhere in the candidate Nifty 50 history. It does not prove that the 49 form a simultaneous Nifty 50 snapshot, nor that this project intends to model the full index rather than a custom subset.
- Sampled candidate Nifty 50 active-member counts were 50 on 2018-04-02, 2019-01-01, 2020-01-01, 2023-07-14, 2024-03-28, 2025-10-01 and 2026-09-30. This is a spot check, not a full independent validation.

## Blocking compatibility and provenance issues

1. **Interval semantics differ.** The candidate uses `[valid_from, valid_to)`; `trader/universe_audit.py` and `apply_point_in_time_membership` currently treat `valid_to` as inclusive. Direct import would misclassify membership on removal/effective dates.
2. **Evidence schema is incomplete for this repository.** The candidate CSV has `source`, `source_url` and `notes`, but not the required `source_published_at`, local `evidence_path` or `evidence_sha256` fields. Some rows are marked `snapshot_floor` and have no source URL.
3. **Raw primary evidence is not archived in the candidate project.** Press-release URLs are useful leads, but the source PDFs must be retrieved, archived and hashed locally before a row can meet this repository's evidence contract.
4. **Aggregate validation is not enough.** The upstream report contains substantial historical failures across indices. Its own documented stronger coverage begins in 2018-04; earlier intervals must not be silently promoted.
5. **Universe definition is unresolved.** The 49 configured tickers are a Nifty 50-style selection, not a complete 50-stock, all-history constituent universe. Applying Nifty 50 membership intervals to a custom selection may be valid only if the explicit strategy rule is “trade only configured names while they are Nifty 50 constituents.”
6. **Tata Motors lineage remains special.** The candidate file labels the long-running row `TMPV` from the 2014 snapshot floor. That is not primary evidence for the pre-demerger security's full economic lineage, the 2025 demerger value allocation, or Yahoo Finance's adjusted OHLCV behaviour. Keep the corporate-action adjustment factor blank until primary exchange price-discovery and vendor-series evidence are reconciled.

## Safe next implementation steps

1. Decide whether the research universe is (a) the complete Nifty 50 with dated additions/removals, or (b) a custom 49-name subset whose eligibility is additionally constrained by Nifty 50 membership.
2. Build a separate candidate-import adapter that preserves the half-open interval convention. Do not silently change the existing evidence schema's inclusive/exclusive meaning.
3. Archive primary NSE Indices press-release PDFs for each relevant inclusion/removal event, record publication and effective dates separately, and compute local SHA-256 hashes.
4. Reconcile symbol aliases and corporate actions, especially TATAMOTORS → TMPV and the demerger.
5. Add tests for removal-day boundary semantics, additions, open intervals, symbol aliases, missing primary documents, and historical index cardinality before allowing the membership file to affect model rows.
6. Only then populate `universe_membership_evidence_matrix.csv` with evidence-backed intervals. Keep all unsupported rows `NOT_VERIFIED`.

## Current outcome

No membership intervals were imported into the production research inputs, no ticker was added or removed, and no model/backtest was rerun. This avoids turning a third-party candidate reconstruction into falsely authenticated point-in-time evidence.
