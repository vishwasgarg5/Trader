# Trader research execution status

Last reviewed: 2026-11-06. This plan tracks research-only work on `feature/p2-liquidity-sector-validation`, stacked on the P1/P2 branch. Production `main` is intentionally unchanged.

## Current decision

**RESEARCH HOLD — no price-feature tuning, model promotion, final-holdout evaluation, merge to production, or live orders.**

The completed P2 experiment fails the pre-registered profitability and statistical-edge gates. Passing CI confirms code execution and reproducibility, not a tradable edge.

Latest full validation: [GitHub Actions run #151](https://github.com/vishwasgarg5/Trader/actions/runs/42080829525), successful on `ac820b586a2ac1fa02b504d691808801d31af1a8`. Unit tests, walk-forward experiment and report upload all passed.

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
- [ ] Confirm the intended universe with the owner; the configured 49-symbol list is not a verified current or historical Nifty 50 universe.
- [ ] Obtain official dated constituent additions/removals and archive source circulars, including delisted constituents.
- [ ] Populate `data/reference/universe_membership.csv` only from those official records.
- [ ] Resolve the missing `TATAMOTORS.NS` price series and TATAMOTORS/TMPV symbol transition/demerger adjustment with source-backed evidence.
- [ ] Independently verify OHLCV adjusted-price lineage, stale/missing sessions and corporate-action factors.
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
- [ ] Reconcile tariff arithmetic against anonymised actual Groww contract notes; account-specific DP concessions remain unverified.
- [ ] Reconcile source delivery history gaps and independently validate price/turnover provenance.
- [x] Evaluate the pre-registered profitability and statistical gates; result is FAIL / HOLD, so do not promote.

### Latest experiment evidence (run #151)

- 16 walk-forward folds; 82,373 labels; 43 ambiguous rows excluded.
- Delivery coverage 99.73%; 1% turnover participation cap applied.
- Cross-sectional AUC 0.5101; logistic baseline 0.5079.
- Model-minus-logistic AUC +0.00384; 95% block-bootstrap interval [-0.00187, +0.00932], includes zero.
- Mean top-five net return across folds -0.1875%; mean net excess over universe +0.0734%; 95% five-day block-bootstrap interval [-0.0252%, +0.1785%], includes zero.
- Predeclared cross-sectional and regime gates both failed; `continue_price_feature_tuning=false`.
- Cash-funded portfolio: 1,148 trades, -17.24% net return, 26.25% realised-equity drawdown.
- Daily mark-to-market portfolio: 1,163 trades, -23.26% net return, 29.23% max daily drawdown and 80.10% peak sector exposure.
- Nifty buy-and-hold comparator: +32.18% before index costs, 15.77% max drawdown over the reported window.
- Daily MTM slippage stress: -23.26% at 2 bps/side; -33.63% at 5 bps; -47.94% at 10 bps; -68.38% at 20 bps.
- Final holdout status: `LOCKED_NOT_EVALUATED`.

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

## External inputs still required

1. Intended universe confirmation.
2. Official historical constituent circulars and archived evidence.
3. Source-backed TATAMOTORS/TMPV transition and corporate-action adjustment.
4. Corporate-action ledger and independent adjusted-price verification.
5. Anonymised Groww contract notes or equivalent actual fee evidence.

Do not fabricate or infer these records. Until supplied and independently validated, Priority 1 is incomplete, the final holdout stays locked, and the strategy remains research-only.
