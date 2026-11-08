# Nifty 50 pilot — Steps 6–12 parallel engineering kickoff

Date: 2026-11-08  
Experiment: `NIFTY50_PILOT_001`  
Branch: `main`  
Status: **ENGINEERING WORKSTREAMS OPEN; NO HISTORICAL EVALUATION AUTHORIZED**

## Scope and safety boundary

This kickoff follows the registered parallel-execution policy. It starts independent implementation and synthetic-test work while upstream evidence remains blocked. It does not waive Steps 2–5 or certify any historical data.

- Universe remains point-in-time Nifty 50 constituents only.
- Exactly five selections per qualifying date; benchmark is Nifty 50 TRI.
- No Nifty 200/500 or all-NSE expansion.
- Step 2 membership, Step 3 identity/corporate actions, Step 4 OHLCV/TRI and Step 5 costs/liquidity remain evidence-blocked.
- Historical labels, portfolio backtests, confirmatory evaluation and holdout access remain disabled.
- Research hold remains active; promotion, paper trading and live execution remain prohibited.
- Pilot GO, if ever reached, means eligibility for a separately approved broader experiment only.

## Workstream register

| Step | Engineering work started / to execute | Acceptance evidence | Hard blocker / prohibited claim |
|---|---|---|---|
| 6 — Fixed-horizon labels | Preserve the isolated five-session label contract; expand boundary, duplicate, missing-data and fail-closed tests. | Synthetic tests for exact five-session interval, strict >1 pp threshold, cost arithmetic and all verified-prerequisite flags. | No historical labels until Steps 2–5 are independently verified and explicitly enabled. |
| 7 — Features and events | Define typed, point-in-time event/feature schemas; enforce publication/first-seen cutoffs, source hashes, issuer/security identity and train-fold-only transformations. | Schema and leakage tests, including late/revised event rejection and as-of-date filtering. | No historical event features until source coverage, timestamps and identity are defensible. |
| 8 — Portfolio construction | Extend the existing cash-funded simulator and diagnostics using synthetic fixtures for cash reservation, partial fills, exposure, sector caps, costs, liquidity and corporate-action accounting. | Deterministic synthetic portfolio tests and one combined weighted portfolio return series. | No historical performance claims using unverified universe, prices, actions or costs. |
| 9 — Power/MDE | Implement a reproducible power/MDE simulation contract; require explicit alpha, target power, seed, eligible-date selection counts, base rate and dependence-preserving time-block resampling. | Synthetic reproducibility tests and report with MDE against the registered 6 pp ceiling. | Do not run or interpret a final empirical power conclusion until design inputs are preregistered and qualifying real observations exist. MDE above 6 pp means INCONCLUSIVE. |
| 10 — Walk-forward validation | Build deterministic chronological folds, six-session purge, fold-local preprocessing/calibration and OOS-only prediction aggregation. | Synthetic chronology, overlap/purge, leakage and train-only-fit tests. | Do not run confirmatory historical evaluation until upstream data gates pass; final holdout stays locked. |
| 11 — Factor and promotion gates | Implement exact factor-definition registry and fail-closed evaluation of the registered gates; bind every gate result to evidence and code/data/config hashes. | Synthetic pass/fail tests proving missing, synthetic or unverified evidence cannot pass. | Factor formulas/inference sensitivities need preregistration; no gate may pass on synthetic or absent evidence. Pilot GO never authorizes promotion or paper/live trading. |
| 12 — Integrity and leakage | Expand cross-cutting schema, hash, point-in-time interval, duplicate, calendar, timestamp and leakage regression checks. | Mutation tests and deliberately corrupted synthetic fixtures that must fail closed. | Integrity coverage cannot be declared complete until real data paths are independently exercised. |

## Evidence-state vocabulary

Every artifact must keep these states separate:

1. `IMPLEMENTED` — code or schema exists.
2. `SYNTHETIC_TESTED` — behavior is tested only with synthetic fixtures.
3. `SOURCE_ACQUIRED` — original source bytes, URL and hash are retained.
4. `DATA_VALIDATED` — content and identity reconciled against independent evidence.
5. `HUMAN_REVIEWED` — identified independent reviewer and review date recorded.
6. `EVALUATION_ELIGIBLE` — all upstream protocol gates are satisfied.

A state advances only when its own evidence exists. CI success is not data validation, predictive edge or approval.

## Current kickoff baseline

- Step 6 label code exists and is synthetic-tested; historical generation remains disabled.
- Step 8 portfolio simulator and diagnostics exist; further synthetic edge-case coverage is required.
- Steps 7, 9, 10, 11 and 12 are opened as engineering workstreams by this register; this document alone does not mark them implemented or complete.
- Step 5 corrected-design Motilal acquisition attempt 003 returned `NOT_ACQUIRED`, with zero eligible links and zero downloads. Its diagnostics are retained in GitHub Actions artifact `motilal-corrected-attempt-003-42443486727`. The one authorized attempt is consumed; no retry or alternate AMC is authorized.
- Step 2 remains open; at least three eligible historical fund snapshots and independent reviewer sign-off remain outstanding.

## Exit rule

Steps 6–12 may advance in parallel only within the engineering/synthetic boundary above. No historical labels, portfolio results, model selection, confirmatory evaluation, holdout access, promotion, paper trading or live execution may be enabled by this kickoff.
