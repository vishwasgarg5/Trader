# Staged model development and broad-universe validation

**Registered:** 2026-11-07  
**Status:** DESIGN REGISTERED; DATA AND SAMPLE RULES BLOCKED; RESEARCH HOLD

## Decision

Adopt a staged workflow to reduce model-development compute without allowing the smaller development sample to stand in for broad-universe evidence:

1. **Stage 1 — development sample:** use a deterministic, representative, point-in-time stratified sample to debug features and compare model families, hyperparameters, calibration and thresholds. All tuning is chronological and uses purged validation folds.
2. **Stage 2 — freeze:** create an immutable manifest covering the estimator, ordered features, preprocessing, labels, calibration, thresholds, risk rules, costs, training window, random seeds, code revision, data snapshot and hashes.
3. **Stage 3 — broad evaluation:** apply the frozen specification to the full eligible point-in-time NSE ordinary-equity universe. Do not refit, recalibrate, change thresholds or otherwise tune on this evaluation set. Report overall and market-cap, liquidity, sector, listing-age and regime results.
4. **Confirmatory holdout:** retain the separately registered final holdout as locked. It is not the broad evaluation tuning set and must be opened only under its existing protocol after all prerequisites pass.

The machine-readable contract is config/staged_model_validation.json.

## Sample design — no arbitrary shortcuts

The development sample must represent more than today's large, liquid constituents. Before Stage 1 is authorized, pre-register:
- sample size and deterministic selection seed;
- market-cap, liquidity, sector and listing-age strata;
- minimum representation and handling of sparse strata;
- point-in-time data availability and as-of selection rules;
- treatment of delisted, suspended, newly listed and renamed securities.

The exact values remain unset because the security master and historical coverage have not been verified. Do not select the sample from current constituents alone, use future market capitalisation/turnover, or silently drop failed histories. Nifty 50 may be a useful development reference but must be supplemented by representative mid/small-cap and liquidity strata from the historical eligible universe.

## Freeze contract

A frozen model version must bind together the serialized estimator and every choice that affects predictions: feature order/definitions, preprocessing, target, calibration, thresholds, ranking, risk sizing, costs, training window, seeds, code SHA, data snapshot SHA-256 and configuration SHA-256. The freeze manifest is written before broad evaluation. Any post-freeze change creates a new version and requires a new unseen evaluation period; the broad evaluation results cannot be fed back into that same version.

## Broad evaluation and comparisons

Run inference with the frozen development artifact; do not train on broad-evaluation labels. Preserve the complete point-in-time security population, including inactive/delisted names during eligible periods. Publish coverage and exclusion counts alongside:
- discrimination and calibration (including Brier score and ROC AUC where defined);
- precision/recall and top-k ranking diagnostics;
- portfolio net returns after reconciled charges, taxes, slippage and liquidity constraints;
- turnover, capacity, drawdown and tail risk;
- dependence-aware confidence intervals and fold stability;
- segment results by market capitalisation, liquidity, sector, listing age and market regime.

Compare with the previous-close zero-return reference, majority-class reference, frozen logistic comparator and predeclared simple-factor/portfolio baselines. A higher accuracy or AUC alone is not acceptance; positive net performance and robust incremental edge must satisfy the existing research gates.

## Current blockers

The present repository state does not authorize either model tuning or a broad-universe run. The existing experiment runner still has legacy Nifty 50 membership and corporate-action gates; those must be deliberately migrated to the approved NSE security-master contract before it can execute the new candidate universe. Current blockers include:
- no independently verified point-in-time NSE listing/delisting/suspension security master;
- historical OHLCV coverage for inactive and delisted securities not established;
- unresolved security identity and corporate-action adjusted-price lineage;
- eligibility, series, liquidity and data-quality thresholds not yet approved;
- broker tariff and slippage assumptions not fully reconciled.

Therefore this commit registers the workflow and its fail-closed contract only. It does not run a misleading small-sample tuning exercise on the legacy 49-symbol snapshot, and it does not authorize full-universe computation.

## Non-negotiable safeguards

Keep RESEARCH_HOLD, promotion_eligible=false, final_holdout=LOCKED_NOT_EVALUATED and live_execution_enabled=false. CI success validates software, not predictive edge or investability.
