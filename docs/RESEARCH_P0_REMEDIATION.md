# P0 Research Remediation Register

**Status:** RESEARCH HOLD  
**Baseline branch:** `main`  
**Last evidence review:** 2026-11-06  
**Policy:** This register is a work tracker, not evidence that any gate has passed. Do not change `config/promotion_gate.json` to approved, do not unlock the confirmatory holdout, and do not enable live execution until the evidence and independent-review requirements below are satisfied.

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
