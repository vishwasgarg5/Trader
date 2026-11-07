# Nifty 50 pilot — Step 6 fixed-horizon labels

Status: **LABEL COMPUTATION CONTRACT IMPLEMENTED; NOT ENABLED FOR HISTORICAL LABEL GENERATION.**

The pilot-specific implementation is isolated in `trader/nifty50_pilot_labels.py`. It does not change or replace `trader/labels.py` and its legacy triple-barrier labels.

## Registered target

For a signal after session T close:

1. Entry is the next eligible session's modeled executable price.
2. Exit is after five entry-to-exit trading sessions.
3. Stock return is the verified total return over the exact entry/exit interval, including dividends and verified corporate-action adjustments.
4. Benchmark return is Nifty 50 TRI over the identical interval.
5. Apply the fixed reference round-trip cost fraction to stock return: `(1 + gross_stock_total_return) * (1 - reference_cost_fraction) - 1`.
6. Relative excess is net stock return minus matched Nifty 50 TRI return.
7. Label 1 only when relative excess is strictly greater than 1 percentage point. Equality and lower values are label 0.

Missing or invalid inputs are `UNRESOLVED`, never negative labels. The interval must explicitly span exactly five entry-session ordinals. Duplicate security/signal-date rows are rejected.

## Fail-closed prerequisites

The function requires explicit verified flags for:
- PIT Nifty 50 membership;
- effective-dated security identity;
- stock total-return inputs;
- Nifty 50 TRI inputs;
- reference execution-cost validation.

If any flag is not exactly true, all requested rows remain unresolved and outcome values are not inspected. The module does not load data, infer a calendar, derive executable prices, estimate costs, or change any evidence ledger.

## Validation and limits

Synthetic tests cover return arithmetic, strict threshold equality, every prerequisite lock, five-session interval validation, missing inputs, duplicates, invalid costs and separation from legacy triple-barrier labels.

A passing test proves the calculation contract only. Historical labels remain prohibited until Steps 2–5 evidence gates are satisfied, the cost profile is independently reconciled, and the project explicitly authorizes the next research stage. No holdout access, evaluation, promotion, paper trading or live execution is enabled.
