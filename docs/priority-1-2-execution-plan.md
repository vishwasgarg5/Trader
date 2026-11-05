# Priority 1 and Priority 2 execution plan

This plan is for research-only work on `feature/p1-p2-data-portfolio-validation`, stacked on the current triple-barrier research revision. No changes are made directly to `main`.

## Priority 1 — prediction and input-data verification

- [x] Add a deterministic SHA-256 manifest builder for frozen input files.
- [x] Require dated membership records to carry HTTPS source URLs, archived evidence paths and matching SHA-256 checksums.
- [x] Reject overlapping membership intervals and keep the strong point-in-time verification flag false until independent evidence review.
- [ ] Obtain official dated Nifty constituent additions/removals and archive the source circulars.
- [ ] Populate `data/reference/universe_membership.csv` from official evidence; do not infer past constituents from today's list.
- [ ] Reconcile all configured symbols with the price panel, including the missing `TATAMOTORS.NS` series in the current experiment.
- [ ] Verify OHLCV source coverage, stale/missing sessions, adjusted-vs-unadjusted semantics and corporate-action factors against official evidence.
- [ ] Freeze and commit or artifact the exact price, delivery, membership and corporate-action inputs with the snapshot manifest.
- [ ] Reconcile NSE delivery history by date and symbol against source download logs; retain coverage gaps explicitly.

## Priority 2 — realistic execution and portfolio validation

- [x] Add a sourced Groww NSE equity-delivery tariff configuration.
- [x] Include per-order brokerage minimum/cap, DP sell fee and low-value DP exemption in the cost function.
- [x] Round cash-equity order quantities down to whole shares and use executed notional for cash and costs.
- [ ] Validate tariff arithmetic against one or more anonymised Groww contract notes; account-specific DP component remains configurable.
- [ ] Model entry/exit execution using next-session open and barrier/gap rules with explicit price-impact and liquidity constraints.
- [x] Enforce integer quantities, available cash, maximum positions, gross exposure and a 1% per-stock participation cap using trailing 20-session NSE rupee turnover in the mark-to-market experiment; fail closed when turnover history is unavailable.
- [x] Add dated sector classification metadata for the configured universe and report daily sector exposure / peak sector concentration; classifications are descriptive, not point-in-time membership evidence.
- [ ] Re-run the complete walk-forward and mark-to-market portfolio diagnostics with Groww costs and the frozen P1 dataset.
- [ ] Compare model returns with buy-and-hold Nifty, exposure-matched Nifty, fixed-factor portfolios and random picks on identical dates.
- [x] Add 2/5/10/20 bps-per-side slippage stress to the Groww-cost mark-to-market report; symbol, sector and regime diagnostics remain descriptive and need interpretation.
- [ ] Require positive absolute net portfolio returns and statistically supported excess returns before any promotion; otherwise retain HOLD.

## Current evidence and blockers

- The prior experiment workflow passed on commit `54a3b92cab361d82af9cfbe0d4056a296b754b5f`, but it used zero brokerage and zero DP defaults. Its results are not the final Groww-cost evaluation.
- Prior mark-to-market diagnostic: net return -9.85%, max daily drawdown 31.78%, 1,204 trades, and no stale daily marks. Over the same dates Nifty buy-and-hold returned +32.18% before index costs; exposure-matched Nifty returned +24.50%.
- Prior random-pick mean net return was -28.65% over 300 simulations. This is a useful comparator, not proof of model profitability.
- The prior data audit found 49 configured symbols but only 48 price series (`TATAMOTORS.NS` absent); point-in-time membership and corporate-action adjustment are not verified.
- Delivery data coverage was 99.73% across the experiment rows, but the historical universe and adjusted-price lineage remain unverified.
- The final holdout remains locked and unevaluated. Do not unlock it until P1 inputs and P2 execution assumptions are reviewed and frozen.
- The current model remains research-only and is not approved for real-money trading.


## Additional execution controls added on 2026-11-05

- NSE full-bhavcopy parsing now captures `TURNOVER_LACS` as rupee turnover and migrates older delivery-only caches by re-fetching affected dates.
- The research merge derives a trailing 20-session average of official NSE turnover; the model and random comparator both enforce a 1% participation cap.
- The mark-to-market simulator fails closed when a requested liquidity cap lacks turnover history and reports daily sector exposure and peak sector concentration.
- The experiment includes 2, 5, 10 and 20 bps-per-side slippage scenarios.
- Sector labels are sourced to the NSE Indices Nifty 50 classification as of 27 February 2026; labels for configured legacy/non-constituent symbols are mapped to the same broad industry taxonomy and are not represented as historical PIT classifications.


- [x] Apply dated membership intervals to research rows when the membership file passes structural, timestamp, evidence-path and SHA-256 audits; if absent, preserve static-universe exploratory research with an explicit unverified status; if present but invalid, fail closed.
