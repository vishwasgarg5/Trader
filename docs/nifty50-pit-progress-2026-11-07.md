# Nifty 50 pilot — evidence progress log (2026-11-07)

Status: **Steps 2–4 remain IN_PROGRESS.** This log records source checks and safe implementation work; it does not certify point-in-time membership, security identity, adjusted prices, or market data.

## Step 2 — official source cross-check

The 18 February 2020 NSE Indices press release initially scheduled the YESBANK removal / SHREECEM inclusion for 27 March 2020 (close 26 March). The official 16 March 2020 superseding release explicitly accelerates that Nifty 50 replacement to 19 March 2020 (close 18 March). The 16 March release names both securities and explicitly refers to the earlier 18 February announcement.

- Initial official source: https://www.niftyindices.com/Press_Release/ind_prs18022020.pdf
- Superseding official source: https://www.niftyindices.com/Press_Release/ind_prs16032020.pdf
- Repository source text: `data/reference/extracted_notice_text/N50-NOTICE-2020-02-18.txt` and `data/reference/extracted_notice_text/N50-NOTICE-2020-03-16.txt`
- Repository transition rows: `N50-2020-YESBANK-OUT` and `N50-2020-SHREECEM-IN`

This confirms why the originally announced March 27 date must not be used as the final effective date. Both rows remain `SAMPLE_ONLY` pending independent human sign-off; this log does not promote them.

## External membership dataset assessment — not imported

A public third-party NSE historical-membership repository was inspected as a possible cross-check only:
https://github.com/aditya-jha/nse-historical-membership

It is not accepted as the pilot's source of truth and no rows were copied into `nifty50_membership.csv`, because:

1. Its own validation report records 13 of 20 internal-consistency invariants failing.
2. Its Nifty 50 history contains `snapshot_floor` intervals without a direct source URL, so those rows do not establish point-in-time effective dates.
3. The inspected history uses `LTM` for an interval beginning in 2023, while the pilot's security identity evidence records LTIM as the official symbol at that time and a later LTIM-to-LTM rename in 2026. This requires source-level identity reconciliation, not ticker substitution.
4. The repository README describes a CC BY 4.0 data licence while the inspected `LICENSE-DATA` text is a CC0 waiver. The licence statement needs clarification before redistributing its data.

The external dataset may be used to identify discrepancies for manual investigation, never to fill missing intervals or to assert verification.

## Source archive reconciliation added to CI

The existing `trader.nifty_notice_reconciliation` audit compares the annual archive inventory, curated notice register, discovery catalog, archived source-document presence and recorded SHA-256 digests. It is diagnostic only and never edits membership rows or review states.

The pilot workflow now runs its focused tests and reconciliation report whenever the reconciliation code, tests, archived source PDFs or extracted notice text change. A passing workflow means the diagnostic ran; it does not mean the evidence coverage is complete or that human review has occurred.

## Remaining Step 2 gates

- Review all in-scope official archive notices for 2018–2024, including OCR-only records and superseding/deferred notices.
- Verify each transition against the original official PDF and reconcile all effective-date snapshots to 50 names, with documented exceptions for special events.
- Build the interval ledger only from reviewed primary-source facts.
- Obtain independent reviewer identity and date for each verified record.

## Steps 3–4 remain blocked

Security aliases and corporate-action adjustment factors still require source-level evidence and independent review. The OHLCV and Nifty 50 TRI CSV contracts remain empty; no historical observations have been invented or imported from an unapproved provider.

## Safety

Nifty 50 pilot only. Protocol remains `DRAFT_NOT_FROZEN`. Holdout access, evaluation, promotion, paper trading and live execution remain unauthorized.


## Engineering closure update — 2026-11-07

The conservative notice-triage queue is implemented and its CI run passed on commit `90ad01f1e96c8506fd61a1a927e583df61e93207` (run #42383794288). It remains a review queue only: all notices require human disposition, and no membership intervals or transitions were promoted.

A diagnostic-only price-index reconstruction module is now present at `trader/nifty50_index_reconstruction.py`, with synthetic tests and this design note: `docs/nifty50-index-reconstruction.md`. It requires exactly 50 distinct reviewed constituents per date, effective-dated security inputs, a supplied divisor, official level observations, and an explicitly supplied positive pre-registered point tolerance. It does not fit parameters, change ledgers, or reconstruct TRI. Synthetic agreement is software validation, not historical evidence.

The pilot workflow was expanded to exercise:
- Membership evidence, interval semantics, special-membership evidence and PIT readiness tests.
- Security alias, corporate-action ledger and transition-register tests.
- Synthetic price-index reconstruction tests.
- Existing notice triage, archive reconciliation, OHLCV/TRI contracts and execution constraints.

### Current in-progress task disposition

- **Step 2 — PIT membership:** triage engineering is implemented; evidence remains blocked. Current audit still reports zero verified transitions and zero complete annual coverage. The 687-row annual notice inventory and 697-row archive catalog remain unresolved under the latest reconciled counts. No human sign-offs were manufactured.
- **Step 3 — security identity/corporate actions:** audit and regression coverage are implemented; evidence remains blocked. Alias mappings are not independently verified and corporate-action adjustment factors are not reconciled to adjusted price history.
- **Step 4 — OHLCV/TRI:** data contracts and readiness checks are implemented; evidence remains blocked. The pilot OHLCV and TRI files remain empty/header-only; no official historical price, total-return or TRI observations were imported.
- **Step 5 — costs/liquidity/fills:** deterministic research constraints and tests are implemented. Empirical evidence remains blocked pending official historical traded-value coverage and independent broker-tariff/contract-note reconciliation.

The index reconstruction diagnostic cannot run on historical data until verified membership, security identity, daily prices, free-float shares/IWF, divisor and official index-level inputs are supplied. Its tolerance also needs explicit protocol registration before real-data comparison.

**Overall roadmap remains 1/13 complete; Steps 2–5 remain IN_PROGRESS, with their safe engineering components implemented and their evidence gates open.** Steps 6–13 remain not started. Protocol remains `DRAFT_NOT_FROZEN`; holdout remains locked and unevaluated; evaluation, promotion, paper trading and live execution remain unauthorized.


### Latest engineering verification

- Model Status run #42384466749 on commit `c55d0557c849bf1aef772ec72b47d1dee5fdeee4` completed successfully: **257 tests passed**; saved-model and safety-gate validation also passed.
- The earlier syntax issue in the reconstruction diagnostic was caught by CI, corrected, and included in the successful 257-test run.
- The dedicated Nifty 50 pilot workflow last confirmed green is #42383794288 on the notice-triage commit. The expanded workflow definition now includes membership/identity/corporate-action and reconstruction tests; the latest full-suite run is the verification evidence for the newly added reconstruction code.
