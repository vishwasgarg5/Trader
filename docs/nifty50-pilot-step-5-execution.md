# Nifty 50 pilot — Step 5 execution assumptions

Status: **IMPLEMENTED AS A DETERMINISTIC RESEARCH CONTRACT; EMPIRICAL VALIDATION PENDING**.

The registered NIFTY50_PILOT_001 execution section remains authoritative:

- 20-session median traded value floor: INR 5 crore.
- Maximum order participation: 2% of the supplied traded-value reference.
- Reference label participation: 1%.
- Per-side slippage scenario: 15 + 25 * sqrt(participation_fraction / 1%) basis points; 40 bps at 1%.
- Stress scenario multiplier: 1.5.
- Unfilled quantity must be recorded, never silently assumed filled.

trader/pilot_execution.py implements these fixed constraints. Liquidity assessment uses the latest 20 unique observations on or before the supplied signal date; fewer than 20 valid sessions are unresolved and fail closed. The fill cap returns requested, filled and unfilled quantities and cannot exceed the participation ceiling.

## Important limits

- The fill cap is a deterministic participation guard, not an intraday execution simulator. It does not establish queue position, spread, auction behavior, market impact calibration or fill probability.
- The slippage curve is a registered scenario assumption, not observed slippage or a guarantee. No historical calibration is claimed.
- The existing Groww charge engine models published delivery tariffs, but tariff arithmetic is not independently reconciled to authenticated anonymised contract notes in this repository. Account-specific DP concessions and contract-note reconciliation remain outstanding.
- NSE turnover inputs must be sourced, timestamped and security-identity reconciled before they can support an empirical pilot run.
- No pilot labels, portfolio simulation, walk-forward evaluation or holdout access is enabled by this change.

## Acceptance criteria covered by code tests

1. Reference and maximum participation slippage values match the registered formula.
2. Participation above 2%, non-finite inputs and invalid orders are rejected.
3. Liquidity uses exactly 20 prior-or-current sessions and ignores future observations.
4. Missing/incomplete or duplicate session history cannot pass.
5. Requested/filled/unfilled quantities are explicit and the filled notional respects the cap.

## Remaining evidence gates

Step 5 is not evidence-complete until official historical traded-value coverage and independent tariff/contract-note reconciliation are supplied and reviewed. CI verifies implementation behavior only.
