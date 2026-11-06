# Trader research execution status

Last reviewed: 2026-11-06. This plan tracks the live `main` branch. P1/P2 engineering fixes are being committed directly to `main`; data provenance, tariff reconciliation and research promotion remain separate evidence gates.

## Current decision

**RESEARCH HOLD — no price-feature tuning, model promotion, final-holdout evaluation, merge to production, or live orders.**

The completed P2 experiment fails the pre-registered profitability and statistical-edge gates. Passing CI confirms code execution and reproducibility, not a tradable edge.

Latest full validation: [GitHub Actions run #171](https://github.com/vishwasgarg5/Trader/actions/runs/42155416537), successful on `06bf56e3cbe826f1194c0b2b893730ea8b7f5bbd`. Unit tests, walk-forward experiment and report upload all passed. The report artifact `triple-barrier-experiment-report` (artifact ID `13475379095`) was downloaded and independently inspected; SHA-256: `e6721cc80b0ae96a1f7d121a4c40a7a2220b3af0c98dcacb0afb4c412f8cb4b6`.

## Priority 0 — leakage-aware research baseline

- [x] Triple-barrier labels with next-session-open entry, gap-aware exits and same-day ambiguous double-touch exclusions.
- [x] Purge training labels using actual label exit dates.
- [x] Walk-forward folds, logistic baseline, shuffled-label controls and fixed-factor comparators.
- [x] Keep the final holdout locked and unevaluated.
- [x] CI validation passed on the research branch.

## Priority 1 — point-in-time data integrity

- [x] Deterministic SHA-256 manifest builder for frozen inputs.
- [x] Membership schema requires HTTPS sources, archived evidence paths and matching SHA-256 checksums.
- [x] Reject overlapping membership intervals; missing history is explicitly unverified and invalid supplied history fails closed.
- [x] Research scope is the complete historical Nifty 50 constituent set on each date, not the current configured 49-symbol subset.
- [ ] Complete the 2018–2024 official Nifty 50 notice inventory, supersession chain and independent source review before creating the PIT ledger.
- [ ] Populate the PIT membership ledger only from primary-source-backed additions/removals using half-open `[valid_from, valid_to)` intervals; keep it blocked until annual completeness and independent review pass.
- [x] Establish the official NSE symbol mapping: `TATAMOTORS` became `TMPV` (Tata Motors Passenger Vehicles Ltd.) effective 2025-10-24; the demerged CV entity listed separately as `TMCV` on 2025-11-12 and was excluded from Nifty indices effective 2025-11-17.
- [ ] Reconcile the missing `TATAMOTORS.NS` history to `TMPV.NS` across the rename and independently verify adjusted-price continuity; do not substitute `TMCV` for the passenger-vehicle history.
- [ ] Independently verify OHLCV adjusted-price lineage, stale/missing sessions and corporate-action factors.
- [x] Correct NSE calendar parsing so naive timestamps remain India-local while timezone-aware timestamps are converted to Asia/Kolkata; add regression tests for both membership and corporate-action audits.
- [x] Make missing OHLCV columns explicit integrity failures rather than silently leaving invalid-row counts as null.
- [x] Make the standard pipeline reject any configured symbol with empty history, fewer than 100 valid OHLCV rows, duplicate NSE calendar dates, invalid date order, missing OHLCV columns or invalid/non-finite OHLCV values.
- [x] Persist a structured `data/reports/data_integrity.json` preflight report before the daily pipeline fails closed; upload it as a GitHub Actions artifact even when signal generation fails.
- [ ] Supply and validate the corporate-action ledger; latest experiment reports it was not provided.
- [ ] Freeze verified price, delivery, membership and corporate-action inputs with the manifest after these checks.

## Priority 2 — realistic execution and portfolio validation

- [x] Source-configured Groww NSE equity-delivery brokerage, statutory charges, DP components and low-value exemption.
- [x] Correct DP exemption to waive only Groww's ₹16.50 component below ₹100 while retaining the separate depository component.
- [x] Whole-share sizing, available-cash enforcement, max positions and exposure constraints.
- [x] NSE full-bhavcopy rupee turnover parsing and trailing 20-session average turnover without look-ahead.
- [x] 1% per-stock participation cap for model and random portfolios; fail closed when turnover history is missing.
- [x] Dated sector taxonomy and daily/peak sector exposure diagnostics.
- [x] 2/5/10/20 bps-per-side slippage stress.
- [x] Compare with Nifty buy-and-hold, exposure-matched Nifty, fixed-factor portfolios and random picks on the research windows.
- [x] Re-run walk-forward and mark-to-market diagnostics with the Groww cost profile.
- [x] Add a component-level contract-note reconciliation helper that excludes slippage and reports per-fee deltas; no actual contract notes have yet been supplied for reconciliation.
- [x] Update NSE cash-market transaction/IPFT component attribution from the 2026-03-01 circular (₹306.99 + ₹0.01 per crore per side); combined exchange/IPFT outflow remains ₹307 per crore per side.
- [ ] Reconcile tariff arithmetic against anonymised actual Groww contract notes; account-specific DP concessions remain unverified.
- [ ] Reconcile source delivery history gaps and independently validate price/turnover provenance.
- [x] Evaluate the pre-registered profitability and statistical gates; result is FAIL / HOLD, so do not promote.

### Latest inspected experiment evidence (run #171; artifact SHA-256 `e6721cc80b0ae96a1f7d121a4c40a7a2220b3af0c98dcacb0afb4c412f8cb4b6`)

- 16 walk-forward folds; 82,366 labelled rows; 43 ambiguous same-day double-touch rows excluded.
- Delivery coverage: 99.732%; 1% turnover participation cap applied.
- Mean cross-sectional AUC: 0.50520; logistic cross-sectional baseline: 0.50790.
- Mean model-minus-logistic cross-sectional AUC: +0.00414; 95% two-fold block-bootstrap interval [-0.00207, +0.00988], includes zero.
- Top-five mean net return across folds: -0.2564%; universe mean net return: -0.2622%; mean net excess: +0.00364%; 95% five-day block-bootstrap interval [-0.1035%, +0.1076%], includes zero.
- Pre-registered cross-sectional and regime gates both failed; `continue_price_feature_tuning=false`, decision `stop_price_feature_tuning`, and `promotion_eligible=false`.
- Cash-funded portfolio: 1,158 trades, -44.47% net return and 45.68% realised-equity drawdown. This realised-equity drawdown understates intra-trade mark-to-market drawdown.
- Daily mark-to-market portfolio: 1,169 trades, -24.39% net return, 29.77% maximum daily drawdown and 80.15% peak sector exposure.
- Nifty buy-and-hold comparator: +32.18% before index costs, 15.77% maximum drawdown; exposure-matched Nifty: +14.18% before index costs.
- Data audit still found only 48 of the configured 49 price histories; `TATAMOTORS.NS` is missing. No official dated membership history or corporate-action ledger was supplied, and adjusted-price lineage remains independently unverified.
- Final holdout status: `LOCKED_NOT_EVALUATED`; no holdout metrics were computed.

Passing CI validates implementation and reproducibility, not data completeness, profitability or trading readiness. The successful run must not be interpreted as passing any promotion gate.

## Priority 3 — freeze and independent review

- [ ] Close P1 evidence gaps and reconcile Groww contract notes.
- [ ] Freeze code SHA, raw-data manifest, universe, cost configuration, execution assumptions and exact evaluation dates.
- [ ] Independent review of labels, purge logic, execution accounting, portfolio MTM and benchmark construction.
- [ ] Confirm pre-registered acceptance criteria remain unchanged.
- [ ] Only if all gates are met, evaluate the untouched final holdout once.

## Priority 4 — forward paper trading

- [ ] Start only after the frozen research process passes its gates.
- [ ] Run a prospective paper ledger with timestamped signals, intended orders, fills/rejections, costs, slippage and daily MTM.
- [ ] Accumulate 60–90 sessions as an operational check; this alone cannot prove a small statistical edge.
- [ ] Review drift, missing data, concentration, drawdown and execution reconciliation.

## Priority 5 — production safeguards

- [ ] Add fail-closed release gates, artifact provenance, monitoring and rollback.
- [ ] Require independent approval before any deployment decision.
- [ ] Keep live execution disabled unless all research, paper and operational gates pass and explicit authorization is given.

## Universe scope confirmed

The research universe is the complete point-in-time Nifty 50 constituent set effective on each date, as frozen in pre-registration T-0003. The configured 49-symbol list is not the research universe and must not be used as a substitute, expanded ad hoc, or described as the historical Nifty 50. The PIT ledger remains blocked until all annual notice, supersession, snapshot and reviewer gates pass.

The 49 configured entries include the legacy `TATAMOTORS.NS` identifier. It must be reconciled to the passenger-vehicle successor `TMPV.NS` and the 2025 demerger before using its series; keep the universe at 49 names and do not include the separate CV ticker as an additional name.

## Source-backed corporate-action and symbol findings

The following primary-source records were located and establish the symbol timeline, but do not by themselves validate the historical Yahoo Finance price series:

- NSE circular [NSE/CML/70875 (2025-10-16)](https://nsearchives.nseindia.com/content/circulars/CML70875.pdf): `TATAMOTORS` → `TMPV`, effective 2025-10-24, with the company renamed Tata Motors Passenger Vehicles Limited.
- NSE Indices press release [2025-10-07](https://www.niftyindices.com/Press_Release/ind_prs07102025.pdf): the demerged CV entity was temporarily represented by `DUMMYTATAM` in affected indices from 2025-10-14 (close 2025-10-13).
- NSE Indices press release [2025-11-13](https://www.niftyindices.com/Press_Release/ind_prs13112025.pdf): the CV entity, listed as `TMCV` on 2025-11-12, was excluded from Nifty indices effective 2025-11-17 (close 2025-11-14).

The research panel must therefore not treat `TATAMOTORS.NS` as an unchanged ticker across this event. Use the passenger-vehicle symbol only after reconciling source-vendor price history and the demerger adjustment; the new CV ticker is not a substitute for the historical passenger-vehicle constituent.

## External inputs still required

1. Complete official point-in-time Nifty 50 membership evidence for every effective date in the 2018-04-01 through 2024-12-31 research window.
2. Source-backed TATAMOTORS/TMPV transition and corporate-action adjustment.
3. Corporate-action ledger and independent adjusted-price verification.
4. Anonymised Groww contract notes or equivalent actual fee evidence.

Do not fabricate or infer these records. Until supplied and independently validated, Priority 1 is incomplete, the final holdout stays locked, and the strategy remains research-only.


## Priority 3 implementation update — rank and concentration controls

The follow-on branch `feature/p3-rankic-sector-risk-controls` adds:
- Daily Spearman rank IC between model scores and realised net returns, with a Newey-West/HAC t-statistic (up to four lags).
- Daily long-short decile net-return spreads with five-session moving-block-bootstrap confidence intervals.
- A 30% hard sector allocation cap in the mark-to-market portfolio simulator; missing sector labels are grouped as `UNKNOWN` rather than bypassing the cap.
- A 50% new-position sizing multiplier after portfolio drawdown reaches 10%.
- Explicit risk-limit metadata in the experiment report and inclusion of universe, broker-cost, sector-taxonomy and holdout-protocol configuration files in the SHA-256 input manifest.
- Regression tests for rank metrics, sector-cap rejection and drawdown-triggered sizing.

These are research-simulator controls, not a live execution authorization. The complete point-in-time Nifty 50 universe is required; current configured symbols are not a substitute. Historical membership, full constituent price coverage and corporate-action evidence gates remain open.


## Direct-main implementation update — 2026-11-06

The following engineering changes are now on `main`:

- Daily pipeline writes a structured preflight report before raising the configured-symbol data-integrity error. The report records missing symbols, price validation, membership evidence and corporate-action evidence gaps, and explicitly keeps promotion/live execution disabled.
- Price validation now checks invalid and duplicate NSE calendar dates and non-increasing date order.
- Universe audit handles empty/invalid date indexes without crashing before the diagnostic can be written.
- Daily workflow uploads the preflight report with `if: always()`; the fast CI workflow now runs on pushes to `main`.
- Groww charge code has a reusable contract-note reconciliation helper. It compares brokerage, STT, stamp duty, exchange, IPFT, SEBI, DP and GST line items, excludes slippage, and does not claim that notes are authenticated.
- NSE circular NSE/FA/73061 (effective 2026-03-01) is recorded in the cost profile. The updated exchange/IPFT split is ₹306.99/₹0.01 per crore per side; combined outflow remains ₹307 per crore per side, so the overall modeled combined rate is unchanged.

These changes improve observability and reconciliation tooling; they do not resolve the external evidence blockers. In particular, the missing TATAMOTORS/TMPV/TMCV total-value price lineage, original source-document archiving, 49-symbol historical membership evidence and actual Groww contract-note reconciliation remain open. Do not bypass the configured-symbol guard or claim Phase 1/2 evidence complete.


## Phase 3 — Research validation (2026-11-06)

- [x] Download and inspect the complete run #182 artifact, not only its green workflow status.
- [x] Reconcile T-0001 results and report SHA-256 in the append-only trial register.
- [x] Record cross-sectional AUC, logistic comparator, block-bootstrap intervals, rank IC, decile spread, fixed 1/2/5-pick sensitivity, regime diagnostics and portfolio net results.
- [x] Add a fail-closed research continuation gate requiring absolute net profitability, a statistically positive model-vs-logistic AUC interval, the predeclared regime check, point-in-time universe evidence and corporate-action adjustment verification.
- [ ] Inspect the next main-branch CI and full experiment artifact after T-0002 code changes.
- [ ] Reconcile historical trial IDs and artifacts (#171, #172, #175, #177 and later runs) before any multiple-testing-adjusted performance claim.

## Phase 4 — Predictive-edge investigation (2026-11-06)

- [x] Compare the current model with logistic regression, shuffled-label nulls and fixed reversal, low-volatility and relative-strength baselines.
- [x] Apply a stopping rule that prevents further price-feature tuning when absolute profitability, incremental predictive significance, regime consistency or data provenance fails.
- [x] Keep the final 12-month holdout locked and unevaluated.
- [x] Add explicit reporting of sector exposure drift after mark-to-market; the 30% control is an entry cap, not a continuously enforced hard cap without rebalancing.
- [ ] Do not start new price-feature or portfolio-threshold searches until Phase 1 data lineage and membership evidence are verified.
- [ ] If data gates are later cleared, pre-register one falsifiable alternative hypothesis on walk-forward data; do not select the one-pick sensitivity as a strategy.
- [ ] Require positive absolute net returns and statistically reliable incremental edge before advancing to the locked holdout protocol.


## Evidence reconciliation update — 2026-11-06

- The selected research universe is the full point-in-time Nifty 50. The membership JSON schema and data gates must preserve dated official index membership and must not fall back to a static 49-symbol subset.nt history as a substitute.
- The corporate-action ledger's two source URLs now point to the NSE corporate-filings page for TMPV and the verified NSE archive path for Circular NSE/CML/70875. The local evidence notes remain explicitly labelled summaries; the original source PDFs have not yet been archived in this repository.
- The NSE circular confirms the TATAMOTORS → TMPV symbol/name change effective 2025-10-24. It does not establish a price adjustment factor.
- The shareholder entitlement was one TML Commercial Vehicles share per eligible Tata Motors share. This is an entitlement ratio, not an adjustment factor for the TMPV OHLCV series. Both ledger factor cells therefore remain null and unresolved; no factor of 1.0 or inferred demerger price split is permitted.
- The NSE corporate-filings page also exposes the 2025-10-09 shareholder communication, 2025-10-01 scheme-effectiveness filing and 2025-10-01 record-date filing. These are the primary records to archive next. Until the original attachments and an independently reproducible price-discovery calculation are archived, adjusted-price continuity remains unverified.
- No historical membership rows were fabricated. The PIT Nifty 50 ledger remains unpopulated until every inclusion/exclusion interval has dated primary-source evidence, including delisted and merged securities.sted or renamed instruments where applicable.
- Gate outcome is unchanged: Priority 1 remains incomplete, final holdout remains locked, promotion/live execution remain disabled.

Primary-source references checked during this reconciliation:
- NSE Listing Circular NSE/CML/70875, 2025-10-16: https://nsearchives.nseindia.com/content/circulars/CML70875.pdf
- NSE TMPV corporate filings (includes the 2025-10-09 shareholder communication and 2025-10-01 scheme/record-date announcements): https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol=TMPV&tabIndex=equity

## Execution update — 2026-11-06 (concurrency and universe evidence)

- Daily Signals run #36 failed after all 118 tests and signal generation passed. The only failing step was publication: a stale generated commit conflicted with newer main versions of data/reports/data_integrity.json and binary models/current_model.joblib. This is an artifact-publication race, not a model/test failure.
- Replaced the unsafe rebase of generated artifacts in .github/workflows/daily.yml with a bounded three-attempt publish loop. When main has advanced, the job resets to the latest origin/main and regenerates outputs before committing; it never force-pushes or attempts to line-merge model binaries. If a push races again, it fetches and rebuilds before retrying.
- Tightened audit_universe: a membership file can no longer pass structural validation when it omits any configured symbol or includes symbols outside the exact configured universe. Added regression tests for both cases.
- Added data/reference/universe_membership_evidence_matrix.csv as a 49-symbol acquisition tracker. All entries remain NOT_VERIFIED; it is deliberately separate from the machine-consumed universe_membership.csv so the tracker cannot be mistaken for verified intervals.
- Corrected the corporate-action ledger to use the exact primary-source document URLs recorded in the evidence notes: the 2025-10-09 shareholder communication and NSE/CML/70875 circular. The source-note files are still summaries, not archived original PDFs.
- The NSE circular confirms TATAMOTORS → TMPV effective 2025-10-24. The shareholder communication's 1:1 figure is an entitlement ratio only. Both price adjustment factors remain null pending an archived exchange price-discovery record and independently reproducible adjustment calculation.
- Validation triggered by these changes: Daily Signals #37 onward, Pull Request CI #29 onward, and Triple Barrier #226 onward. Treat them as pending until their completed conclusions and job logs are inspected.
- Keep final holdout locked and promotion/live execution disabled. Use the frozen full point-in-time Nifty 50 universe only after its evidence and price-coverage gates pass.


## Execution update — 2026-11-06 (Yahoo Finance cache contention)

- Daily Trader Signals #43 passed all 121 unit tests but failed during price download: yfinance reported SQLite `OperationalError('database is locked')` for BAJAJFINSV.NS, after which the fail-closed preflight correctly stopped on empty history.
- The run log points to threaded yfinance download/cache contention, not proof of a missing listing or valid zero-price history.
- Changed the downloader to `threads=False` so yfinance cache/database writes are serialized, and added a regression test asserting the non-threaded call.
- Commits: `e43c1cf` (serialize downloads), `381ef0d` (test).
- CI #32 passed with 121 tests before this downloader change. CI #33/#34, Daily Signals #44/#45 and Triple Barrier #231/#232 were triggered by the new commits and must be inspected before considering the fix validated.
- Keep the pipeline fail-closed if any symbol still has insufficient or unusable data. Do not silently drop BAJAJFINSV.NS or substitute another ticker.


## Scope correction — full point-in-time Nifty 50 supersedes legacy 49-name notes

The current approved research universe is the **complete point-in-time Nifty 50**, with dated membership effective on each session and half-open intervals `[valid_from, valid_to)`. This decision supersedes older passages in this execution plan that describe the configured 49 symbols as the intended universe. The configured 49-name list is not a valid substitute for the historical Nifty 50 and must not be used to omit historical constituents. Research window: 2018-04-01 through 2024-12-31. No PIT ledger, full-universe price panel, model experiment, or holdout evaluation is authorized until the annual source inventory, supersession review, constituent snapshots, complete price coverage, symbol/corporate-action lineage, and independent review gates pass.
