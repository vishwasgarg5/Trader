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


## Decision update — full point-in-time Nifty 50 selected

The research-universe ambiguity is resolved: use the **complete Nifty 50 constituent set effective on each date**, not the configured 49-name snapshot. This decision is frozen in pre-registration T-0003 in `docs/experiment-trial-register.md`.

Implementation guardrails now fixed:
- Research starts no earlier than 2018-04-01.
- Membership intervals are half-open `[valid_from, valid_to)`; `valid_from` is included and `valid_to` excluded.
- Membership is effective from the official effective date. Publication/announcement time is retained separately and must not be later than the effective date for the membership fact to be usable at that effective date.
- Missing/delisted constituent price history is a fail-closed data-coverage blocker. No silent omission, imputation, or survivor-only fallback.
- Official NSE circular spot checks will be labelled `SAMPLE_VERIFIED`, never full-series verified.
- TATAMOTORS/TMPV/TMCV remains quarantined until the full security and adjusted-price lineage is reconciled.
- The final holdout remains locked; no performance experiment is authorized until source authentication, full-universe coverage, and the corporate-action blockers are resolved.

The existing interval audit/application now uses the half-open convention, with tests for inclusion on `valid_from`, exclusion on `valid_to`, future-effective membership not making earlier rows eligible, and rejection of zero-length intervals. This is a semantics correction only: the unauthenticated candidate data has not been imported, the static 49-symbol configuration has not been represented as the full universe, and no model/backtest has been run.

**Current status: universe decision registered; interval semantics corrected and regression-tested; full-universe data integration remains BLOCKED pending primary-source checks and complete price coverage.**


## Preliminary official-circular spot-check (candidate data is not accepted)

The pinned candidate CSV was compared against official NSE Indices press releases for selected Nifty 50 additions/removals spanning 2018–2024. These are useful independent primary-source checks, but the PDF files have **not yet been archived into this repository and hashed locally**. Accordingly, no evidence-matrix row is promoted to `SAMPLE_VERIFIED` and no candidate interval is approved for pipeline use.

| Published circular | Effective date | Nifty 50 transition stated by NSE Indices | Candidate CSV comparison |
|---|---|---|---|
| [2018-08-28](https://niftyindices.com/Press_Release/ind_prs28082018.pdf) | 2018-09-28 | LUPIN out; JSWSTEEL in | Candidate dates match |
| [2019-02-25](https://niftyindices.com/Press_Release/ind_prs25022019.pdf) | 2019-03-29 | HINDPETRO out; BRITANNIA in | Candidate dates match |
| [2020-03-16](https://www.niftyindices.com/Press_Release/ind_prs16032020.pdf) | **2020-03-19** | YESBANK out; SHREECEM in; NSE explicitly accelerated the originally announced March 27 change | **MISMATCH:** candidate CSV retains YESBANK through 2020-03-27 and starts SHREECEM on 2020-03-27. Both boundaries are eight calendar days late. The February 18 announcement alone is insufficient; the March 16 superseding circular controls. |
| [2021-02-23](https://www.niftyindices.com/Press_Release/ind_prs23022021.pdf) | 2021-03-31 | GAIL out; TATACONSUM in | Candidate dates match |
| [2022-09-01](https://www.niftyindices.com/Press_Release/ind_prs01092022.pdf) | 2022-09-30 | SHREECEM out; ADANIENT in | Candidate dates match |
| [2023-07-04](https://www.niftyindices.com/Press_Release/ind_prs04072023.pdf) | 2023-07-13 | HDFC out; LTIMindtree in | Candidate date matches, but candidate symbol is `LTM` while the circular says `LTIM`; alias is unresolved |
| [2024-02-28](https://www.niftyindices.com/Press_Release/ind_prs28022024.pdf) | 2024-03-28 | UPL out; SHRIRAMFIN in | Candidate dates match |
| [2024-08-23](https://www.niftyindices.com/Press_Release/ind_prs23082024.pdf) | 2024-09-30 | DIVISLAB and LTIM out; BEL and TRENT in | Candidate dates match, but the candidate uses `LTM` rather than circular symbol `LTIM` for the outgoing constituent |

This spot-check includes more than 10 constituent transition records across seven calendar years. It already identifies a substantive effective-date error (the 2020 Yes Bank/Shree Cement transition) and an unresolved symbol alias (LTIMindtree). Therefore, the third-party CSV cannot be imported as-is, even for the stronger-coverage period. Every event must be reconciled against the controlling, latest official circular, including accelerated, deferred, superseded, merger and delisting changes—not merely the first announcement.

The 2020 finding also illustrates the look-ahead/data-lineage hazard: the candidate interval was apparently closed against the original February schedule, despite a later March 16 official decision changing the effective date. The implementation must resolve superseding notices chronologically and retain both announcement timestamp and final effective date. No performance run is authorized on the candidate CSV.


## Additional primary-source checks added on 2026-11-06

The following official NSE Indices press releases were opened and checked directly during the continuation audit. Their constituent events are recorded in the transition register as `SAMPLE_ONLY`; none is treated as complete annual coverage until the original PDF bytes are committed, SHA-256 is computed from those bytes, all superseding notices are checked, and a reviewer signs off.

| Published circular | Effective date | Nifty 50 transition stated by NSE Indices |
|---|---|---|
| [2018-02-21](https://www.niftyindices.com/Press_Release/ind_prs21022018.pdf) | 2018-04-02 | AMBUJACEM, AUROPHARMA and BOSCHLTD out; BAJAJFINSV, GRASIM and TITAN in |
| [2019-08-28](https://www.niftyindices.com/Press_Release/ind_prs28082019.pdf) | 2019-09-27 | IBULHSGFIN out; NESTLEIND in |
| [2020-07-02](https://www.niftyindices.com/Press_Release/ind_prs02072020_1.pdf) | 2020-07-31 | VEDL out; HDFCLIFE in |
| [2020-08-20](https://www.niftyindices.com/Press_Release/ind_prs20082020.pdf) | 2020-09-25 | INFRATEL and ZEEL out; DIVISLAB and SBILIFE in |
| [2022-02-24](https://www.niftyindices.com/Press_Release/ind_prs24022022_1.pdf) | 2022-03-31 | IOC out; APOLLOHOSP in |

The 2021-02-23, 2022-09-01, 2023-07-04, 2024-02-28 and 2024-08-23 events remain documented in the preceding spot-check table. These checks are not an exhaustive inventory: the official archive contains other releases and special corporate-action updates that still require event-by-event screening.

## Register integrity correction

The transition CSV had notes containing commas without CSV quoting. That caused affected records to parse as more than the required 16 columns. The register was normalized by quoting the notes field and rechecked with a quote-aware parser: all 34 current records now have exactly 16 columns. This repairs file structure only; it does not authenticate any row or change the `SAMPLE_ONLY` status.

## Current gate

- Transition register: 34 candidate records; all remain `SAMPLE_ONLY`.
- Annual coverage: 0/7 years marked complete.
- Original official PDF archive and hashes: not yet complete.
- Full interval ledger: absent; `data/reference/universe_membership.csv` is still missing.
- Alias and corporate-action evidence: still unverified.
- Full-universe price panel and experiment: not authorized.


## JIOFIN temporary Nifty 50 membership — special-event ledger

The ordinary ADD/REMOVE transition ledger cannot represent the 2023 demerger episode safely. A separate `data/reference/nifty50_special_membership_events.csv` now records the three required phases:

1. `JIOFIN_SPINOFF_DUMMY` added effective 2023-07-20 (close 2023-07-19), with 51 securities represented and SPOS-derived constant-price treatment.
2. Dummy member replaced by listed `JIOFIN` on 2023-08-21, retaining 51 securities; the NSE listing notice was published 2023-08-18.
3. Listed `JIOFIN` removed effective 2023-09-07 (close 2023-09-06), returning the index to 50 securities.

The July 17 NSE Indices announcement describes temporary spun-off entity inclusion and the demerger price treatment. The September 5 NSE Indices release states JIOFIN was listed on August 21 and confirms the September 7 removal; NSE circular FAOP58243 independently confirms the NIFTY 50 exclusion.

Primary source URLs:
- https://nsearchives.nseindia.com/web/sites/default/files/2023-08/PR_cc_17072023.pdf
- https://www.niftyindices.com/Press_Release/ind_prs05092023.pdf
- https://archives.nseindia.com/content/circulars/FAOP58243.pdf
- https://www.niftyindices.com/Methodology/Method_NIFTY_Equity_Indices.pdf

The ledger uses a synthetic key `JIOFIN_SPINOFF_DUMMY`; it does not assert that this was the vendor's tradable ticker. It deliberately does not infer the SPOS-derived price or use the 1:1 shareholder entitlement as a price-adjustment factor. The event auditor requires all three phases, the 51-to-50 constituent-count transitions, primary HTTPS URLs, original source files and SHA-256 hashes, and reviewer sign-off before it can pass.

**Current status:** three event rows are present, all remain `SAMPLE_ONLY`, and no original PDF bytes have been archived or hashed. The experiment runner now calls this special-event audit before data download and fails closed while it is unresolved. The JIOFIN episode is therefore represented in the research evidence plan but is not yet approved for operational interval or price-panel construction.


## 2020 supersession chronology correction — 2026-11-06

The 2020 YESBANK/SHREECEM NIFTY 50 transition has been reconciled against the original and superseding NSE Indices releases:

- **2020-02-18 original periodic-review release** (ind_prs18022020.pdf) announced YESBANK exclusion and SHREECEM inclusion effective 2020-03-27 (close 2020-03-26).
- **2020-03-16 superseding release** (ind_prs16032020.pdf) explicitly references the February 18 and March 12 notices and accelerates the NIFTY 50 replacement to 2020-03-19 (close 2020-03-18), due to the Yes Bank reconstruction scheme.
- The transition register now records the original announcement date as 2020-02-18, the effective date as 2020-03-19, and the March 16 notice in the superseding-notice fields for both YESBANK and SHREECEM.
- The 2020-03-23 deferment and 2020-05-13 nullification/reinitiation releases apply to changes that were still scheduled for 2020-03-27; the May 13 release explicitly excludes NIFTY 50 and NIFTY Bank because those indices had already been rebalanced effective 2020-03-19. These documents must remain in the annual supersession audit trail, but they do not reverse the March 19 NIFTY 50 replacement.

Primary sources:
- https://www.niftyindices.com/Press_Release/ind_prs18022020.pdf
- https://www.niftyindices.com/Press_Release/ind_prs16032020.pdf
- https://www.niftyindices.com/Press_Release/ind_prs23032020.pdf
- https://www.niftyindices.com/Press_Release/ind_prs13052020.pdf

All affected transition rows remain SAMPLE_ONLY until independent document review and annual inventory reconciliation are complete.


## Transition-source archival and content spot-check — 2026-11-06

The transition-register archive workflow now downloads the primary source PDF for every candidate transition row, validates the PDF signature and approved NSE/Nifty Indices host, stores the source once per URL, and writes the local path plus SHA-256 back to the ledger. The successful archival run covered all 34 candidate rows, 13 unique original-notice PDFs, and the separate 2020-03-16 superseding notice (14 distinct PDFs total). The 2020-02-18 original notice and 2020-03-16 superseding notice are both attached to the YESBANK and SHREECEM rows.

Content spot-checks of the official documents confirmed the candidate transition details for:
- 2018-04-02: AMBUJACEM, AUROPHARMA and BOSCHLTD out; BAJAJFINSV, GRASIM and TITAN in.
- 2018-09-28: LUPIN out; JSWSTEEL in.
- 2019-03-29: HINDPETRO out; BRITANNIA in.
- 2019-09-27: IBULHSGFIN out; NESTLEIND in.
- 2020-03-19: YESBANK out; SHREECEM in, accelerated from the original March 27 schedule.
- 2020-07-31: VEDL out; HDFCLIFE in.
- 2020-09-25: INFRATEL and ZEEL out; DIVISLAB and SBILIFE in.
- 2021-03-31: GAIL out; TATACONSUM in.
- 2022-03-31: IOC out; APOLLOHOSP in.
- 2022-09-30: SHREECEM out; ADANIENT in.
- 2023-07-13: HDFC out; LTIM in (official symbol LTIM).
- 2024-03-28: UPL out; SHRIRAMFIN in.
- 2024-09-30: DIVISLAB and LTIM out; BEL and TRENT in.

This is a document-content spot-check of the currently registered candidate transitions, not proof that the annual notice inventory is exhaustive. All 34 transition rows remain SAMPLE_ONLY, and all seven annual coverage rows remain NOT_STARTED until independent review, supersession inventory completion, and snapshot reconciliation are complete.


## Preliminary annual notice inventory — 2026-11-06

A separate `data/reference/nifty50_annual_notice_inventory.csv` has been added so notice discovery is not conflated with actual constituent-transition rows. It currently contains 20 candidate/negative-screen records across 2018–2024. The archive workflow now downloads each inventory PDF from approved NSE/Nifty Indices hosts, validates the PDF signature, stores it locally, and records SHA-256.

The initial inventory captures the currently registered Nifty 50 transition releases, the 2020-03-16 superseding notice, and the JIOFIN temporary-member/listing/removal documents. It also screens three documents that are not Nifty 50 constituent changes: the 2021-09-15 review release (Nifty India Manufacturing and strategy indices only), the 2021-12-08 Nifty50 Value 20 annual review, and the 2024-09-25 IDEA revocation release (its table does not list Nifty 50). These negative screens are deliberately retained so they cannot later be mistaken for omitted constituent transitions.

The official methodology states that Nifty 50 is reviewed semi-annually using six-month data ending January and July, with any replacements implemented on the last trading day of March and September; it also permits additional reconstitution for mergers, demergers, delistings and other specified events. Consequently, the annual audit must cover both scheduled review windows and ad-hoc corporate-action/exception notices. A list of known additions/removals is not enough to establish completeness.

**Current gap:** the 20-row inventory is a discovery baseline, not an exhaustive annual notice inventory. In particular, 2021's September broad-market review search remains unresolved; the screened September 15 and December 8 notices are not evidence that no other Nifty 50 review notice existed. All seven rows in `nifty50_annual_coverage.csv` therefore remain `NOT_STARTED`, all transitions remain `SAMPLE_ONLY`, and no PIT membership ledger is authorized.

Primary discovery and scope references:
- NSE Indices methodology: https://archives.nseindia.com/content/indices/Method_NIFTY_Equity_Indices.pdf
- Official review tutorial: https://niftyindices.com/resources/tutorial/review-of-indices
- Official annual press-release archive: https://www.niftyindices.com/press-release
- 2021-09-15 release: https://www.niftyindices.com/Press_Release/ind_prs15092021.pdf
- 2021-12-08 strategy-index release: https://www.niftyindices.com/Press_Release/ind_prs08122021.pdf
- 2024-09-25 superseding/revocation release: https://www.niftyindices.com/Press_Release/ind_prs25092024.pdf


## COVID-period supersession chain — 2026-11-06 audit continuation

The annual notice inventory has been extended with three primary-source candidates for the March–May 2020 rebalancing chain:
- 2020-03-23 deferment: https://www.niftyindices.com/Press_Release/ind_prs23032020.pdf. It defers the March 27 index rebalancing until further notice.
- 2020-03-25 further deferment: https://www.niftyindices.com/Press_Release/ind_prs25032020.pdf. It defers the ETF/index-fund concentration-norm related changes previously announced for March 27.
- 2020-05-13 nullification/reinitiation: https://www.niftyindices.com/Press_Release/ind_prs13052020.pdf. It explicitly says March 27 replacements are null and void **except NIFTY 50 and NIFTY Bank**, because those indices had already rebalanced effective March 19. It restarts the review for the other indices.

This establishes the important distinction: the March 23 and May 13 actions did not reverse the Nifty 50's already-effective March 19 YESBANK/SHREECEM replacement. The March 25 notice concerns the subsequent concentration-norm implementation delay. All three are retained as CANDIDATE notice records with archived PDFs and SHA-256 hashes; line-by-line independent review remains open and none is promoted to VERIFIED. The 2021-09-20 broad-market review release is still an unresolved discovery item: the official archive lists the release, but a verified direct PDF source URL has not yet been established, so no guessed URL was added.


## 2021 methodology and notice discovery — 2026-11-06 continuation

- The official archive lists a September 20, 2021 release titled “Replacements in indices w.e.f. September 30, 2021”. The archive listing confirms the release exists, but its direct official PDF URL and Nifty 50 scope have not yet been verified. No URL or membership transition has been inferred from the title alone.
- The September 15, 2021 PDF is verified and archived; its semi-annual replacement section covers Nifty India Manufacturing and does not establish a Nifty 50 constituent change. This is a scope screen only, not annual completeness.
- The February 23, 2021 methodology-change PDF is a separate control document from the same-day replacement notice. Its official URL has been located: https://www.niftyindices.com/Press_Release/ind_prs23022021_1.pdf. It states that periodic reconstitutions take effect from the last working day (beginning of day) of March, June, September and December, replacing the prior first-working-day-after-F&O-expiry convention. This matters directly to effective-date and half-open interval construction. The PDF is documented here but is not yet in the hash-validated inventory: the current archive workflow requires a pre-existing 64-character digest before it will download and calculate the actual digest. No placeholder hash was inserted.
- The official archive also lists April 22, June 15, August 23 and October 22, 2021 replacement/methodology notices. Their direct PDFs and parent-index scope remain to be retrieved and screened. The archive page is the primary discovery index: https://www.niftyindices.com/press-release.
- 2021 annual coverage remains NOT_STARTED; no transition is promoted to VERIFIED and no PIT ledger is authorized.


## 2021-10-22 scope screen — 2026-11-06 continuation

The official October 22, 2021 NSE Indices press release has now been retrieved and inspected:

- Official PDF: https://www.niftyindices.com/Press_Release/ind_prs22102021.pdf
- It revises index-maintenance guidelines and lists replacements effective October 29, 2021.
- The replacement section covers NIFTY 500, NIFTY500 Multicap 50:25:25, NIFTY Midcap 150, NIFTY Midcap 50, NIFTY Midcap 100, NIFTY 200, NIFTY LargeMidcap 250, NIFTY MidSmallcap 400, NIFTY Microcap 250 and NIFTY Total Market. It does not list NIFTY 50.
- This is a verified negative scope screen for the parent NIFTY 50 constituent set, not proof of annual completeness.
- The PDF has not yet been archived and hashed in this repository. It is therefore documented as an audit finding only and has not been inserted into the hash-validated annual inventory.

The September 20, April 22, June 15 and August 23, 2021 archive entries still require direct-PDF retrieval and scope review. Do not infer a direct URL from the archive title. The 2021 annual gate remains NOT_STARTED.


## 2019-04-09 notice scope screen — 2026-11-07

The archived official NSE Indices release dated 2019-04-09 was inspected using its extracted full text and checked against the archived source record:

- Official PDF: https://www.niftyindices.com/Press_Release/ind_prs09042019.pdf
- The notice is explicitly titled “Replacements in NIFTY 10 Year SDL Index” and states the changes become effective 2019-04-10.
- It excludes 12 state-development loan securities and includes five, identified by ISIN in the annual notice register.
- It contains no flagship NIFTY 50 constituent-change section. This is a negative scope screen, not a Nifty 50 transition.
- Original PDF is already archived at `data/reference/source_documents/NOTICE-NSE-ARCHIVE-2019-04-09-901e85ba7a3b.pdf`; the inventory SHA-256 is retained unchanged: `3e6150ffa9a74b71d401c8e8cfa98b807db7d2d93a97872223644390cdc945f6`.
- The annual inventory and notice register now classify it as `SCREENED_NO_NIFTY50_CHANGE` / `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`. No reviewer identity or sign-off date is fabricated.

This closes the AI scope-screen task for this single notice only. It does not complete 2019 annual archive reconciliation, supersession review, year-end snapshot reconciliation, or independent human review; 2019 coverage remains `NOT_STARTED` and the PIT membership ledger remains unauthorized.


## 2019-04-23 notice pair scope screen — 2026-11-07

Two separate archived official NSE Indices releases dated 2019-04-23 were inspected:

1. [NIFTY G-Sec fixed-income replacements](https://www.niftyindices.com/Press_Release/ind_prs23042019.pdf), effective 2019-05-02. It changes NIFTY 11-15 yr G-Sec, NIFTY 15 yr and above G-Sec, and NIFTY Composite G-Sec only. Seven affected government-security ISINs are recorded in the notice register. No flagship NIFTY 50 constituent section/change was found.
2. [NIFTY 10 Year SDL replacements](https://www.niftyindices.com/Press_Release/ind_prs23042019_1.pdf), effective 2019-04-24. It excludes four state-development loans and includes three, all recorded by ISIN in the notice register. No flagship NIFTY 50 constituent section/change was found.

Both original PDFs are already archived in `data/reference/source_documents/` and their existing SHA-256 digests are retained in the inventory/register. The two inventory rows are now `SCREENED_NO_NIFTY50_CHANGE`; the register rows remain `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`. These are AI negative scope screens only, not independent human verification or annual completeness evidence.
