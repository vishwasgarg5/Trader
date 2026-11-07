# P0 Research Remediation Register

**Status:** RESEARCH HOLD  
**Baseline branch:** `main`  
**Last evidence review:** 2026-11-07  
**Policy:** This register is a work tracker, not evidence that any gate has passed. Do not change `config/promotion_gate.json` to approved, do not unlock the confirmatory holdout, and do not enable live execution until the evidence and independent-review requirements below are satisfied.

## Latest verified checkpoint — 2026-11-07

**Latest model/evidence refresh:** `057010e5223dca69215bbb8d53d4e3acae1d1c53` (daily model/report refresh).  
**Research-data change:** full-text scope screening of archived official NSE Indices notices; see completed items below.  
**Progress-register updates:** `d0a17dee8651ded8b6ce6a9e94799e53005cdb08` and `cccf649ce703a43a5584e68d2186f283a300cc88`.

### Completed this run

- Full-text screened the archived 2019-04-08 NSE Indices replacement notice. Excel Crop Care (EXCELCROP) is replaced by Sundaram Clayton (SUNCLAYLTD) in Nifty 500, Nifty Smallcap 250 and Nifty MidSmallcap 400 only; no flagship Nifty 50 constituent section or change. Effective 2019-04-15. Source SHA-256: `a4ff43189ea06cc6dbf53f3c5ac615b1b0c030fe0678c6fe38e991a5a05716af`. Registered as AI-reviewed pending independent human sign-off, with a regression test.

- Full-text screened the archived 2018-01-08 NSE Indices notice. Its 13 numbered sections cover other indices; no flagship NIFTY 50 constituent section is present. Its 2018-02-05 effective date precedes this research window's 2018-04-01 start. Source SHA-256: `364784c98963a7bc2d28fa19d7b0c5377063178e9215669b1c7b1dfcdc8981f2`.
- Full-text screened the archived 2019-12-18 NSE Indices notice. Its constituent sections cover NIFTY 500, NIFTY Smallcap 250 and NIFTY MidSmallcap 400 only; no flagship NIFTY 50 section is present. It is distinct from the 2019-12-19 impact-cost notice. Source SHA-256: `1a82bef95e25f8b6760dc06b4d6d443416193aaa22322627edb7f33784a0fc0e`.
- Full-text screened the archived 2018-05-24 NSE Indices demerger/replacements notice. It lists changes across 14 other indices, with no flagship NIFTY 50 constituent section. Effective 2018-06-29. The original PDF is already archived and SHA-256 verified as `bbc4a4c04cae7a1ff924e8b3ef3f7acc6b3a9da069a1d6a36cfe0ae99189e957`; scope classification remains AI-reviewed pending human sign-off. Added a regression test.
- Updated the annual inventory, discovery catalog, scope-review table, human review queue notes and 2018/2019 coverage notes. Both decisions are explicitly AI-only: `AI_SCOPE_EXCLUSION_PENDING_HUMAN_SIGNOFF`; the 95-row human queue remains `PENDING_HUMAN_REVIEW`, with no reviewer or verified event fields filled.
- Added `tests/test_nifty_unregistered_scope_review.py`. It checks the archived PDF bytes against the recorded SHA-256, the extracted-text scope evidence, and the continued human-review hold.

- Full-text screened the archived 2024-10-10 NSE Indices Shariah review notice. It records 15 exclusions and 5 inclusions in Nifty500 Shariah only and explicitly says Nifty50 Shariah and Nifty Shariah 25 are unchanged; it contains no flagship Nifty 50 constituent transition. Effective 2024-10-31. Source SHA-256 from the archived inventory: `a24e99d89476f28d37954f5c818dbace7c6125d448ec050c1e0f949b6a0dd169`. Registered as AI-reviewed pending independent human sign-off, with a regression test.

- Full-text screened the archived 2018-06-20 NSE Indices HT Media replacement notice. Replacements affect Nifty 500, Nifty Smallcap 250, Nifty MidSmallcap 400 and Nifty Media only; no flagship Nifty 50 constituent section or change is present. Effective 2018-06-29. Source SHA-256: `e4853e8962fd4df7156f7d7077d3df3aba6ba354eb368a771036e3c7a6ec9385`. Registered as AI-reviewed pending independent human sign-off, with a regression test.
- Full-text screened the archived 2018-12-14 NSE Indices 13-page replacement/review notice. It covers multiple broad-market and strategy indices, including Nifty50 Value 20, but no flagship Nifty 50 constituent section or change. Effective 2018-12-28. Source SHA-256: `0a9fb1a90d69d6d34c7893409ff33806ce153fd464b2ed7809ac132362c6afe0`. Registered as AI-reviewed pending independent human sign-off, with a regression test.
- Full-text screened the archived 2019-01-21 NSE Indices four-page replacement notice. Dena Bank and Vijaya Bank changes apply to Nifty 500, Nifty Smallcap 250, Nifty Smallcap 100, Nifty MidSmallcap 400, Nifty Dividend Opportunities 50, Nifty PSU Bank and Nifty500 Value 50 only; no flagship Nifty 50 constituent section or change. Effective 2019-01-28. Source SHA-256: `ff617ab210bc5a1519e2432ebc03a0737b2a103245b2cab0767442be7edd323d`. Registered as AI-reviewed pending independent human sign-off, with a regression test.

### Verified evidence state

- Annual notice inventory: 684 rows — 586 `DISCOVERED_UNREVIEWED`, 20 `CANDIDATE`, 78 `SCREENED_NO_NIFTY50_CHANGE`. 682 rows have archived PDF paths and hashes; three source URLs still return non-PDF responses: 2018-06-05, 2019-07-16 and 2023-03-14. Their contents remain unresolved; retain the retrieval failures and do not infer PDF contents.
- Archive discovery catalog: 697 rows (558 title candidates, 139 non-candidates). Fifteen catalog-only records remain outside the annual inventory after URL-level reconciliation; they are not silently counted as reviewed. Official PDF text has been inspected for three priority controls: the 2024-02-27 and 2024-08-16 notices only announce future Index Maintenance Sub-Committee review meetings, while the 2024-12-02 Strides Pharma corporate adjustment applies to Nifty Microcap 250 and Nifty Total Market only. All three controls are now registered in the curated notice register as `LOCATED_NOT_ARCHIVED`; original PDF bytes and hashes remain outstanding.
- Curated notice register: 113 rows. Review states: 24 `ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW`, 86 `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`, and 3 `LOCATED_NOT_ARCHIVED`. The three unarchived rows are the two 2024 meeting announcements and the 2024 Strides corporate-action control; none is counted as archived evidence.
- Transition register: 34 rows, all `SAMPLE_ONLY`. Special-membership ledger: 3 JIOFIN dummy/listed/removal events, all `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`. The membership-interval file has zero data rows.
- Annual coverage: all seven years (2018–2024) remain `NOT_STARTED`; every `official_notice_search_complete` flag remains false. Supersession review, authoritative snapshot reconciliation and independent sign-off are not complete.
- Security identity: three alias/lineage rows exist, but none is verified (one explicitly `UNVERIFIED`, two lack a verification status). The two TMPV-related corporate-action rows still have blank adjustment factors and no archived original source documents.

### Model and monitoring — diagnostic only

The latest daily run generated successfully, but its reported metrics did not improve: 7,252 chronological test rows (2026-03-24 to 2026-10-29), five-session horizon and purge, before costs; accuracy 0.6208 versus majority-class accuracy 0.6338, ROC AUC 0.574, Brier score 0.2333. This is not a previous-close or buy-and-hold comparison and does not establish incremental edge. The monitoring report still fails the point-in-time-membership check (zero rows), corporate-action lineage check (two unresolved rows), and accuracy-versus-majority check; prediction-drift history is only 2 of the 40 required sessions.

**Promotion remains `RESEARCH_HOLD`; `promotion_eligible=false`; `live_execution_enabled=false`; the confirmatory holdout remains locked and unevaluated.**

### Workflow evidence

- CI status for test commit `ccfce85861129c218c3372c396096bedde4bdce9` returned no status-check records at review time; do not treat that commit as CI-verified.

- [CI run 42340279629](https://github.com/vishwasgarg5/Trader/actions/runs/42340279629) — success; unit tests (including the new scope-review test) and source reconciliation passed.
- [Source archive run 42340279660](https://github.com/vishwasgarg5/Trader/actions/runs/42340279660) — success; archive/hash checks passed, with the three explicit non-PDF retrieval warnings above; no further archive commit was needed.
- [Daily model run 42340279658](https://github.com/vishwasgarg5/Trader/actions/runs/42340279658) — success; model/report generation and fail-closed monitoring completed. This workflow success does not pass a research gate.
- [CI run 42344869876](https://github.com/vishwasgarg5/Trader/actions/runs/42344869876) — success on commit `6258d1f1820bc58b39bc5a1191561ee4576bbe8d`; dependency installation, full test suite, saved-model/metrics/safety-gate validation, status report generation, and artifact upload all completed successfully.

### Next action

Continue full-text screening of the remaining archived annual-inventory notices, prioritising the next chronological candidate after 2019-04-08. Preserve AI-only scope decisions as pending independent human sign-off. Retry the three non-PDF source URLs with diagnostics and keep their contents unresolved. Do not start full-universe performance experiments until point-in-time membership and security/price lineage are independently established. The three 2024 catalog-only controls remain `LOCATED_NOT_ARCHIVED`; archive their original PDFs byte-for-byte through the approved source-archiver environment when available.

## Gate 0 — Historical point-in-time Nifty 50 universe

Current evidence:
- `data/reports/data_integrity.json` reports membership history as not provided, zero rows, invalid, and not point-in-time verified.
- `data/reference/nifty50_annual_coverage.csv` has annual coverage marked `NOT_STARTED` for 2018–2024.
- `config/universe.txt` is a legacy 49-symbol snapshot and is not a historical membership source.

Required deliverables:
1. Archive the complete official notice inventory for every review and ad-hoc event in scope from 2018-04-01 onward.
2. Record source URL, publication/effective dates, source file, SHA-256, notice type, supersession/cancellation relationship, and screening outcome for every notice.
3. Reconstruct effective-dated constituent intervals, including temporary additions/removals, exits, delisted securities, and all symbol/issuer changes.
4. Reconcile each effective date against authoritative Nifty 50 constituent snapshots or equivalent independent evidence.
5. Complete annual coverage fields only after all notices and supersessions for that year have been reviewed.
6. Obtain an independent reviewer and timestamp; preserve unresolved discrepancies as blockers.

Acceptance criteria:
- Membership intervals use documented half-open `[valid_from, valid_to)` semantics.
- Every date in the research window maps to exactly 50 valid constituents, except explicitly documented index-event timing conventions.
- No constituent is included before its effective entry or retained after its effective exit.
- The historical price panel includes every constituent while it was a member, including exited names.
- Audit reports point-in-time verification true only when provenance, coverage, reconciliation, and independent review all pass.

## Gate 1 — Security identity and historical prices

Required deliverables:
1. Build an effective-dated security identity ledger linking ticker, issuer/security identifier, exchange symbol, and predecessor/successor identity.
2. Preserve delisted and renamed instruments rather than silently dropping or merging them.
3. Retrieve daily OHLCV for the full historical constituent set and benchmark over the declared research period.
4. Reconcile session calendars, missing observations, stale prices, duplicates, zero-volume rows, and invalid OHLC relationships.
5. Record provider, retrieval time, raw-file hash, adjustment mode, and data version for every source panel.

Acceptance criteria:
- Every membership interval has a corresponding auditable price history or an explicitly adjudicated missing-data exception.
- No future membership, identifier, or price information leaks into a historical decision.
- Missing sessions are distinguished from exchange holidays, suspensions, and vendor outages.
- Price data is reproducible from immutable source snapshots.

## Gate 2 — Corporate actions and return construction

Current evidence:
- `data/reference/corporate_actions.csv` contains two TMPV-related records with blank adjustment factors and local source summaries.
- The integrity report explicitly states that adjusted-price lineage is not independently verified and has two unresolved adjustment-factor rows.

Required deliverables:
1. Archive original issuer/exchange documents, not only local summaries; hash each original document.
2. Record action terms, ex-date, record date where relevant, effective date, predecessor/successor identifiers, and authoritative source.
3. Reconcile raw and adjusted OHLCV around each split, bonus, dividend, demerger, rights issue, and symbol/issuer change.
4. Define price-return versus total-return benchmark treatment and dividend reinvestment assumptions.
5. Validate vendor-adjusted series against independently calculated action-adjusted series.

Acceptance criteria:
- No unresolved action affecting the research period remains in the price panel.
- Every factor is derived from documented action terms and independently checked.
- Dividend and demerger treatment is consistent between securities, portfolio returns, and benchmark.
- The integrity report cannot pass based solely on file presence, metadata, or checksums.

## Gate 3 — Broker costs and execution assumptions

Required deliverables:
1. Obtain anonymised actual Groww delivery contract notes covering representative buy/sell transactions.
2. Reconcile brokerage, STT, exchange transaction charges, GST, SEBI charges, stamp duty, and any applicable depository charges against the tariff effective on each trade date.
3. Validate spread, slippage, liquidity, partial fills, and market-impact assumptions.
4. Compare calculated charges with contract-note debits/credits and explain every variance.

Acceptance criteria:
- Cost calculations match actual notes within a documented rounding tolerance.
- Buy and sell sides, taxes, and effective tariff dates are tested separately.
- Backtests use conservative, evidence-backed execution assumptions and report gross and net results.

## Gate 4 — Statistical and portfolio validation

Required deliverables:
1. Re-run the pre-registered walk-forward protocol on the verified point-in-time universe.
2. Compare against previous-close, simple ranking, and other predeclared baselines.
3. Report rank IC, decile monotonicity, calibration, precision/recall, and regime-specific results.
4. Use dependence-aware inference (including HAC and block-bootstrap methods where appropriate) and correct for multiple testing/model selection.
5. Re-run Triple Barrier and portfolio construction diagnostics without changing the locked final holdout.
6. Report turnover, concentration, drawdown, capacity, gross return, net return, and benchmark-relative return.

Acceptance criteria:
- Positive net performance is not sufficient by itself: pre-registered incremental-edge confidence bounds and risk constraints must also pass.
- All evaluation windows, purge/embargo rules, seeds, data versions, and model parameters are recorded.
- A STOP result remains a STOP; no post-hoc threshold changes or repeated holdout tuning.
- Independent research review signs off on the complete evidence bundle.

## Gate 5 — Confirmatory holdout and prospective paper trading

Required deliverables:
1. Keep the confirmatory holdout inaccessible to model selection until Gates 0–4 pass.
2. Freeze and hash code, features, parameters, data, baseline, and evaluation protocol before one confirmatory run.
3. Run prospective paper trading with timestamped pre-outcome predictions, realistic execution costs, and immutable outcome records.
4. Monitor model/data drift, portfolio exposure, sector concentration, turnover, drawdown, and operational failures.

Acceptance criteria:
- Confirmatory results meet all pre-registered statistical and economic thresholds.
- Prospective paper trading meets its pre-registered duration and risk/performance criteria.
- Independent approval is recorded.
- Promotion and live execution remain separate approvals; live execution stays disabled absent explicit authorization.

## Current blockers (do not mark complete without evidence)

| Gate | Current status | Evidence needed |
|---|---|---|
| Historical membership | BLOCKED | Complete official notice inventory, membership intervals, snapshots, independent review |
| Historical price panel | BLOCKED | Full constituent histories, identity continuity, source provenance |
| Corporate actions | BLOCKED | Original documents, resolved factors, adjusted/raw reconciliation, total-return policy |
| Broker costs | BLOCKED | Actual contract-note reconciliation and execution-cost validation |
| Statistical edge | NOT ESTABLISHED | Verified-universe walk-forward and dependence-aware incremental-edge evidence |
| Confirmatory holdout | LOCKED | All prior gates passed and protocol frozen |
| Paper trading | NOT COMPLETE | Prospective timestamped evidence and independent review |

## Execution discipline

- Work on `main` only as requested; each change must be small, reviewable, and tested.
- Never manufacture historical membership, adjustment factors, broker evidence, or performance results.
- Never mark a gate passed because a workflow succeeded or a file exists.
- Update this register with evidence paths, hashes, reviewer, and test/run identifiers as work is completed.
- Preserve `RESEARCH_HOLD`, `promotion_eligible: false`, and `live_execution_enabled: false` until every required approval is satisfied.

### Additional notice screen — 2019-05-02 (AI-only; human sign-off pending)

- Full-text screened the archived official two-page NSE Indices PDF dated 2019-05-02. It announces replacements in the NIFTY 10 Year SDL fixed-income index effective 2019-05-03: seven state-development-loan securities are excluded and no inclusion is listed. The document contains no flagship NIFTY 50 constituent section or equity membership change.
- Archived PDF SHA-256 `9a214f365f39a82cf4eca8b25ec750ab844099799fe6ca75f9da20e387861079` matches the annual inventory record.
- Updated the annual notice inventory, unregistered-candidate scope-review table, and notice review queue. The classification is `AI_SCOPE_EXCLUSION_PENDING_HUMAN_SIGNOFF`; queue remains `PENDING_HUMAN_REVIEW`. No reviewer identity or verified event fields were fabricated.
- Source: https://www.niftyindices.com/Press_Release/ind_prs02052019.pdf

### Additional notice screen — 2019-05-07 (AI-only; human sign-off pending)

- Full-text screened the archived official NSE Indices release dated 2019-05-07. It announces two inclusions (Kerala and Rajasthan state development loans) in the NIFTY 10 Year SDL fixed-income index effective 2019-05-08, with no exclusions. The notice contains no flagship NIFTY 50 equity constituent section or membership event.
- Archived PDF SHA-256: `b820afda2c7659791b566f736a80d9e82c6dab57b90e3f8a2db843a074161697`, matching the annual inventory record.
- Updated the annual notice inventory, unregistered-candidate scope-review table, notice review queue, and regression test. Classification remains `AI_SCOPE_EXCLUSION_PENDING_HUMAN_SIGNOFF`; manual queue remains `PENDING_HUMAN_REVIEW`.
- Source: https://www.niftyindices.com/Press_Release/ind_prs07052019.pdf

### CI correction and additional notice screen — 2019-05-08

- Investigated workflow run `42352509491`: the test suite reported `1 failed, 203 passed`. The failure was a schema-value mismatch in the 2019-05-07 inventory row: the new row used a custom fixed-income classification while the regression test and established inventory convention require `NO_FLAGSHIP_NIFTY50_CONSTITUENT_CHANGE`. Normalized that row to the established value; this is a metadata correction, not a change to the source interpretation.
- Full-text screened the official NSE Indices release dated 2019-05-08. It excludes One Point One Solutions (`ONEPOINT`) from NIFTY SME EMERGE effective 2019-05-09 (close of 2019-05-08), with no inclusion. This is not a NIFTY 50 membership event.
- Archived PDF SHA-256: `af50b6eebba05bfe608c1659cd1158e60a5a0b3a399a10a82ccc7d2e6a98e6c3`, matching the annual inventory record. Updated the annual inventory, unregistered-candidate scope review, notice review queue and regression test. AI scope review remains pending human sign-off.
- Source: https://www.niftyindices.com/Press_Release/ind_prs08052019.pdf

### CI schema fix — 2019-05-02 classification normalization

- Follow-up CI run `42352645468` still failed because the 2019-05-02 archived SDL notice retained the legacy value `EXPLICIT_FIXED_INCOME_SDL_NOT_NIFTY50_EQUITY`, while the regression test's canonical inventory contract requires `NO_FLAGSHIP_NIFTY50_CONSTITUENT_CHANGE` for all notices screened as not changing the flagship NIFTY 50.
- Normalized the 2019-05-02 inventory value to the canonical classification. The source interpretation, PDF hash, extracted text, and pending-human-review status are unchanged. This corrects the schema inconsistency; it does not constitute human approval.
- Official archive index lists the 2019-05-02, 2019-05-07 and 2019-05-08 press releases in its May 2019 archive. The 10 Year SDL index is a fixed-income portfolio of State Development Loans, not the flagship equity constituent list. Source: https://www.nseindia.com/static/nse-indices/press-releases


### Additional notice screen — 2019-05-14 (AI-only; human sign-off pending)

- Full-text screened the archived official two-page NSE Indices release dated 2019-05-14. It announces seven exclusions and two inclusions (Kerala and Rajasthan State Development Loan securities) in the NIFTY 10 Year SDL fixed-income index, effective 2019-05-15. The extracted notice contains no flagship NIFTY 50 equity constituent section or membership event.
- Archived PDF SHA-256: `a9bcace20ecf5038aa5101a32bfef7dae803f9fb9be2836da4a45a207eb45c1d`, matching the annual inventory record. Extracted text: `data/reference/extracted_notice_text/NSE-ARCHIVE-2019-05-14-cde78c64905a.txt`.
- Updated the annual notice inventory, unregistered-candidate scope-review table, human review queue and regression test. AI scope classification remains pending independent human sign-off; manual review remains `PENDING_HUMAN_REVIEW` and no verified symbol or reviewer fields were populated.
- Source: https://www.niftyindices.com/Press_Release/ind_prs14052019.pdf


### Additional notice screen — 2019-06-13 (AI-only; human sign-off pending)

- Full-text screened the archived official 11-page NSE Indices PDF dated 2019-06-13. It announces changes effective 2019-06-28 across NIFTY 500, NIFTY Midcap 150, NIFTY Smallcap 250, NIFTY LargeMidcap 250, NIFTY MidSmallcap 400, NIFTY Midcap 50, NIFTY Infrastructure and strategy indices. The document contains no flagship NIFTY 50 constituent section or membership event.
- Archived PDF SHA-256: `b05a59c604e1c29cfa00931c71d6ffd9fbe201f0be60b78235eb6f9635447338`, matching the annual inventory record. Extracted text: `data/reference/extracted_notice_text/NSE-ARCHIVE-2019-06-13-8b59c9ce840e.txt`.
- Normalized the annual inventory row to `NO_FLAGSHIP_NIFTY50_CONSTITUENT_CHANGE` / `SCREENED_NO_NIFTY50_CHANGE`, updated the manual review queue evidence note, and added a regression case that checks the archived PDF hash and extracted text. The scope register remains AI-reviewed pending human sign-off; manual queue remains `PENDING_HUMAN_REVIEW`; no reviewer or verified event fields were populated.
- Source: https://www.niftyindices.com/Press_Release/ind_prs13062019.pdf
