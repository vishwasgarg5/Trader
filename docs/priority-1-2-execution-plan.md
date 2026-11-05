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
- [ ] Enforce integer quantities, available cash, maximum positions, gross exposure and per-stock turnover participation in every portfolio run.
- [ ] Add sector classifications and report sector concentration; no sector concentration conclusion is valid while sector labels are absent.
- [ ] Re-run the complete walk-forward and mark-to-market portfolio diagnostics with Groww costs and the frozen P1 dataset.
- [ ] Compare model returns with buy-and-hold Nifty, exposure-matched Nifty, fixed-factor portfolios and random picks on identical dates.
- [ ] Run robustness checks by symbol, sector, regime, time period and slippage/cost stress.
- [ ] Require positive absolute net portfolio returns and statistically supported excess returns before any promotion; otherwise retain HOLD.

## Current evidence and blockers

- The prior experiment workflow passed on commit `54a3b92cab361d82af9cfbe0d4056a296b754b5f`, but it used zero brokerage and zero DP defaults. Its results are not the final Groww-cost evaluation.
- Prior mark-to-market diagnostic: net return -9.85%, max daily drawdown 31.78%, 1,204 trades, and no stale daily marks. Over the same dates Nifty buy-and-hold returned +32.18% before index costs; exposure-matched Nifty returned +24.50%.
- Prior random-pick mean net return was -28.65% over 300 simulations. This is a useful comparator, not proof of model profitability.
- The prior data audit found 49 configured symbols but only 48 price series (`TATAMOTORS.NS` absent); point-in-time membership and corporate-action adjustment are not verified.
- Delivery data coverage was 99.73% across the experiment rows, but the historical universe and adjusted-price lineage remain unverified.
- The final holdout remains locked and unevaluated. Do not unlock it until P1 inputs and P2 execution assumptions are reviewed and frozen.
- The current model remains research-only and is not approved for real-money trading.
