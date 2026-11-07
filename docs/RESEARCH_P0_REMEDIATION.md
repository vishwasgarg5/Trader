# P0 Research Remediation Register

**Status:** RESEARCH HOLD  
**Baseline branch:** `main`  
**Last evidence review:** 2026-11-07  
**Policy:** This register is a work tracker, not evidence that any gate has passed. Do not change `config/promotion_gate.json` to approved, do not unlock the confirmatory holdout, and do not enable live execution until the evidence and independent-review requirements below are satisfied.

## Latest verified checkpoint — 2026-11-07

**Current main head:** `057010e5223dca69215bbb8d53d4e3acae1d1c53` (daily model/report refresh).  
**Research-data change:** `13a0dac571ab5c75fd91622fb0536999d56f7a65` — full-text scope screening of two archived official notices.

### Completed this run

- Full-text screened the archived 2018-01-08 NSE Indices notice. Its 13 numbered sections cover other indices; no flagship NIFTY 50 constituent section is present. Its 2018-02-05 effective date precedes this research window's 2018-04-01 start. Source SHA-256: `364784c98963a7bc2d28fa19d7b0c5377063178e9215669b1c7b1dfcdc8981f2`.
- Full-text screened the archived 2019-12-18 NSE Indices notice. Its constituent sections cover NIFTY 500, NIFTY Smallcap 250 and NIFTY MidSmallcap 400 only; no flagship NIFTY 50 section is present. It is distinct from the 2019-12-19 impact-cost notice. Source SHA-256: `1a82bef95e25f8b6760dc06b4d6d443416193aaa22322627edb7f33784a0fc0e`.
- Updated the annual inventory, discovery catalog, scope-review table, human review queue notes and 2018/2019 coverage notes. Both decisions are explicitly AI-only: `AI_SCOPE_EXCLUSION_PENDING_HUMAN_SIGNOFF`; the 95-row human queue remains `PENDING_HUMAN_REVIEW`, with no reviewer or verified event fields filled.
- Added `tests/test_nifty_unregistered_scope_review.py`. It checks the archived PDF bytes against the recorded SHA-256, the extracted-text scope evidence, and the continued human-review hold.

### Verified evidence state

- Annual notice inventory: 684 rows — 592 `DISCOVERED_UNREVIEWED`, 20 `CANDIDATE`, 72 `SCREENED_NO_NIFTY50_CHANGE`. 681 rows have archived PDF paths and hashes; three source URLs still return non-PDF responses: 2018-06-05, 2019-07-16 and 2023-03-14. Their contents remain unresolved; retain the retrieval failures and do not infer PDF contents.
- Archive discovery catalog: 697 rows (558 title candidates, 139 non-candidates). Fifteen catalog-only records remain outside the annual inventory after URL-level reconciliation; they are not silently counted as reviewed. Next full-text dispositions should prioritize the 2024-02-27 and 2024-08-16 Index Maintenance Sub-Committee meeting notices and the 2024-12-02 Strides Pharma corporate-adjustment notice.
- Curated notice register: 104 rows — 16 `NIFTY50_CHANGE`, 2 `NIFTY50_CONFIRMATION`, 82 `NO_CHANGE`, 1 `METHODOLOGY_CONTROL`, 2 `CORPORATE_ACTION_CONTROL`, and 1 `NO_MEMBERSHIP_CHANGE`. Review states: 24 `ARCHIVED_HASHED_PENDING_INDEPENDENT_REVIEW` and 80 `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`.
- Transition register: 34 rows, all `SAMPLE_ONLY`. Special-membership ledger: 3 JIOFIN dummy/listed/removal events, all `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`. The membership-interval file has zero data rows.
- Annual coverage: all seven years (2018–2024) remain `NOT_STARTED`; every `official_notice_search_complete` flag remains false. Supersession review, authoritative snapshot reconciliation and independent sign-off are not complete.
- Security identity: three alias/lineage rows exist, but none is verified (one explicitly `UNVERIFIED`, two lack a verification status). The two TMPV-related corporate-action rows still have blank adjustment factors and no archived original source documents.

### Model and monitoring — diagnostic only

The latest daily run generated successfully, but its reported metrics did not improve: 7,252 chronological test rows (2026-03-24 to 2026-10-29), five-session horizon and purge, before costs; accuracy 0.6208 versus majority-class accuracy 0.6338, ROC AUC 0.574, Brier score 0.2333. This is not a previous-close or buy-and-hold comparison and does not establish incremental edge. The monitoring report still fails the point-in-time-membership check (zero rows), corporate-action lineage check (two unresolved rows), and accuracy-versus-majority check; prediction-drift history is only 2 of the 40 required sessions.

**Promotion remains `RESEARCH_HOLD`; `promotion_eligible=false`; `live_execution_enabled=false`; the confirmatory holdout remains locked and unevaluated.**

### Workflow evidence

- [CI run 42340279629](https://github.com/vishwasgarg5/Trader/actions/runs/42340279629) — success; unit tests (including the new scope-review test) and source reconciliation passed.
- [Source archive run 42340279660](https://github.com/vishwasgarg5/Trader/actions/runs/42340279660) — success; archive/hash checks passed, with the three explicit non-PDF retrieval warnings above; no further archive commit was needed.
- [Daily model run 42340279658](https://github.com/vishwasgarg5/Trader/actions/runs/42340279658) — success; model/report generation and fail-closed monitoring completed. This workflow success does not pass a research gate.

### Next action

Reconcile the 15 catalog-only records, starting with the two 2024 review-meeting controls and the Strides Pharma corporate-action control; archive/hash any in-scope source PDFs and link them to the subsequent review notices. Then continue full-text screening of the 592 unreviewed annual-inventory rows, retry the three non-PDF source URLs with diagnostics, and preserve all human-review and snapshot-reconciliation gates. Do not start full-universe performance experiments until point-in-time membership and security/price lineage are independently established.

Draft PR #9 remains unmerged; AI scope screening is not human approval.

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
