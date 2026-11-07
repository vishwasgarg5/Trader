# Nifty 50 pilot registration — Issue #11

**Status: DRAFT_NOT_FROZEN.** This document registers the experiment boundary and safety state; it does not certify data, freeze unresolved implementation assumptions, or authorize evaluation.

## Scope and outcome restriction

- Experiment: `NIFTY50_PILOT_001`.
- Universe: point-in-time Nifty 50 constituents only.
- Select exactly five securities per qualifying date. At a complete 50-name cross-section this is 10%; do not dynamically increase the number of picks when names are missing.
- Benchmark: Nifty 50 TRI over the identical return interval.
- No Nifty 200, Nifty 500 or all-NSE expansion in this pilot.
- Pilot GO means **eligible for a separately approved broader experiment only**. It does not authorize promotion, paper trading or live trading.

## Target

Signal after close T; enter next eligible session at a modeled executable price; exit after five trading sessions. The stock outcome is total return including dividends and verified corporate-action adjustments. Compare with Nifty 50 TRI over the identical interval. The positive label is strictly greater than 1% net relative excess after a fixed reference-cost profile. Equality at 1% is negative. Missing or unresolved outcomes are excluded as unresolved, not converted to class zero.

The existing triple-barrier implementation remains available for legacy experiments. The pilot must explicitly opt into the fixed-horizon label in its own implementation issue.

## Portfolio and execution assumptions

The proposed reference capital is ₹1 crore, with ₹25 lakh and ₹5 crore sensitivities. The proposed liquidity screen is ₹5 crore 20-session median traded value; maximum order participation is 2% ADV and label reference participation is 1% ADV. Proposed slippage is `15 + 25 * sqrt(participation / 1%)` basis points per side (40 bps per side at 1%). These are **not frozen** until Groww tariff and execution assumptions are validated. Unfilled orders must never be assumed executed.

## Statistical contract

- Precision@10% is top-five precision.
- Minimum precision-lift MDE ceiling: 6 percentage points. If simulated MDE exceeds 6 pp, outcome is automatically INCONCLUSIVE.
- Use chronological walk-forward folds, six-session purge and training-fold-only preprocessing/calibration.
- Proposed primary inference: Newey–West with 10 daily lags and a 20-session time-block bootstrap. Sensitivity details must be frozen before evaluation.
- DSR uses one combined weighted daily portfolio series, not five sleeves as independent observations.
- Historical trial census is incomplete; no DSR claim is permitted until reconstructed.

## Data and sample eligibility

At least five clean development years, 1,000 qualifying cross-sectional dates and at least 30 eligible securities per qualifying date are required. Historical membership, security identities, executable OHLCV, total returns, Nifty 50 TRI, corporate-action evidence, publication timestamps and sector limitations require verification. The 2026-02-27 sector configuration is not historical point-in-time sector history.

## Holdout conflict

The repository's existing `config/final_holdout_protocol.json` still specifies 12 months. This registration records the new pilot rule: 24 months if at least seven clean development years exist; otherwise 18 months if five to under seven years exist. Exact dates are not selected until clean-data availability is verified and must be selected before viewing holdout returns. Issue #23 owns the reconciliation; this registration does not unlock or alter holdout data.

## Explicit non-authorization

`evaluation_authorized=false`, `holdout_access_authorized=false`, `promotion_eligible=false`, `paper_trading_eligible=false`, `live_execution_enabled=false`, and `full_universe_experiment_authorized=false`.

## Outstanding freeze items

1. Verify historical Nifty 50 membership and security identity lineage.
2. Verify Nifty 50 TRI and stock total-return data.
3. Validate broker tariffs, slippage and fill assumptions.
4. Specify remaining power simulation design inputs and run the simulation.
5. Freeze exact factor formulas and inference sensitivity analysis.
6. Reconstruct the historical trial census for DSR.
7. Reconcile the legacy 12-month holdout configuration under issue #23.
8. Obtain independent protocol review and record SHA-256 hashes.

Run the validator with:

```bash
python -m trader.pilot_protocol
pytest -q tests/test_nifty50_pilot_protocol.py
```
