# Gate audit — 2026-11-06

## Decision

**RESEARCH HOLD.** No turnover experiments, new features, universe expansion, final-holdout evaluation, promotion or live execution are authorized by this audit.

## Scope and trace

The relative-excess interval is produced in `trader/research.py` by `walk_forward_evaluate`:

1. For each out-of-sample signal date, calculate the mean net return of the model's top-five picks minus the same-date universe mean net return.
2. Pool those daily spreads in chronological order across the cross-sectional walk-forward folds.
3. Pass that daily series to `block_bootstrap_mean_ci`, which uses a circular moving-block bootstrap with five trading-day blocks, 2,000 resamples, and seed 42052.
4. Store the result as `top5_minus_universe_net_return_block_bootstrap_95pct`.
5. `trader/experiment.py` passes the cross-sectional experiment metrics to `evaluate_research_continuation_gate`.

This is the correct dependence-aware distribution for the pre-registered daily relative-excess estimand. It is not the separate AUC comparator distribution: incremental model-versus-logistic AUC is bootstrapped over paired walk-forward folds using circular two-fold blocks. The two intervals must not be interchanged.

## Finding

Before this audit, the research gate checked only that the relative-excess interval's lower endpoint was present and greater than zero. That correctly rejected a valid interval crossing zero, including **-0.09 to +0.12**, but it did not validate the upper endpoint, endpoint ordering, finiteness, 95% confidence level, or expected bootstrap method. The experiment's separate `cross_pass` summary duplicated the lower-endpoint-only check.

Therefore, the current implementation did not demonstrate that the quoted crossing-zero interval could pass this specific lower-bound check. The defect was incomplete interval validation and duplicated gate logic—not evidence that the interval was intentionally treated as statistically positive. The report artifact containing the quoted interval must still be checked against the exact field above before claiming a byte-for-byte reconciliation.

## Correction on main

- Added one shared validator requiring the expected bootstrap method, 95% confidence level, finite lower and upper endpoints, correctly ordered endpoints, and both endpoints strictly above zero.
- Applied it to the relative-excess research gate and to the experiment's `cross_pass` diagnostic.
- Applied the corresponding fold-bootstrap method validation to the model-versus-logistic AUC gate.
- Added a regression fixture with relative-excess CI **[-0.09, +0.12]** and positive mean return / positive fold count; the gate must return `STOP`.
- Added malformed-interval and wrong-bootstrap-method regression cases.

## Interpretation of the reported interval

If **-0.09 to +0.12** is the 95% interval in `top5_minus_universe_net_return_block_bootstrap_95pct`, it crosses zero and cannot satisfy the corrected gate. A positive point estimate, a majority of positive folds, or a positive upper endpoint cannot override that result.

## Validation still required

The commits are on `main`. The CI run triggered by these commits must pass the complete unit suite and regenerate the walk-forward experiment artifact. The generated artifact must then be inspected to verify the exact interval field, its method, confidence level, endpoints, and `research_continuation_gate` result. Until that artifact check completes, the gate audit is **code-corrected, CI/artifact verification pending**, and research remains on hold.
