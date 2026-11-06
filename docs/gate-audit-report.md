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

Before this audit, the research gate checked only that the lower endpoint of the **cross-sectional experiment's** relative-excess interval was present and greater than zero. It did not validate the upper endpoint, endpoint ordering, finiteness, 95% confidence level, or expected bootstrap method. The experiment's separate `cross_pass` summary duplicated the lower-endpoint-only check. Importantly, the gate receives `cross_sectional_experiment.fold_metrics`; it does not consume the top-level pooled-model interval, even though both objects use the same CI field name.

## Correction on main

- Added one shared validator requiring the expected bootstrap method, 95% confidence level, finite lower and upper endpoints, correctly ordered endpoints, and both endpoints strictly above zero.
- Applied it to the relative-excess research gate and to the experiment's `cross_pass` diagnostic.
- Applied the corresponding fold-bootstrap method validation to the model-versus-logistic AUC gate.
- Added a regression fixture with relative-excess CI **[-0.09, +0.12]** and positive mean return / positive fold count; the gate must return `STOP`.
- Added malformed-interval and wrong-bootstrap-method regression cases.

## Interpretation of the reported interval

The quoted **-0.09% to +0.12%** interval is the top-level pooled-model interval, not the cross-sectional interval consumed by the research gate. The gate's input is `cross_sectional_experiment.fold_metrics.top5_minus_universe_net_return_block_bootstrap_95pct`. A positive result on that cross-sectional estimand does not imply that the pooled-model interval is positive; these are distinct estimands and must be labelled by full JSON path.

## Validation still required

The commits are on `main`. The CI run triggered by these commits must pass the complete unit suite and regenerate the walk-forward experiment artifact. The generated artifact must then be inspected to verify the exact interval field, its method, confidence level, endpoints, and `research_continuation_gate` result. Until that artifact check completes, the gate audit is **code-corrected, CI/artifact verification pending**, and research remains on hold.

## Post-correction CI and artifact verification — 2026-11-06

Workflow run #208 completed successfully on commit `7ca4a69151377eb9fc9fd2721a5e4d87989cea05`. The unit-test step, walk-forward experiment step, and artifact upload step all completed successfully.

The uploaded artifact `triple-barrier-experiment-report` was inspected. Its primary relative-excess field is:

- Method: `circular_moving_block_bootstrap`
- Block length: 5 trading days
- Resamples: 2,000
- Confidence level: 95%
- Lower: `-0.0009678749075539621`
- Upper: `0.0009288992178137709`

The interval crosses zero. The generated `research_continuation_gate` reports `STOP`; the interval check is false; promotion eligibility and live execution are both false. The 95% AUC-difference interval also crosses zero (`-0.0024317086322898475` to `0.006798290330470413`) using its separate two-fold bootstrap. The final holdout remains `LOCKED_NOT_EVALUATED`, with no holdout metrics computed.

**Reconciliation caveat:** the top-level pooled-model interval in run #208 is approximately `-0.000968 to +0.000929` in decimal-return units (about `-0.0968% to +0.0929%`). Its cross-sectional gate-input interval is approximately `-0.0000757 to +0.0017711` (about `-0.0076% to +0.1771%`). Both cross zero, and the corrected gate rejects the cross-sectional interval.

## Final audit disposition

The code correction and regression tests are validated by successful CI, and the generated experiment independently confirms a STOP decision. The gate inconsistency is resolved for the current main-branch artifact. The historical interval-source reconciliation remains open. Research remains **HOLD** because the gate fails on profitability, regime, incremental AUC, point-in-time universe, and corporate-action evidence as well as relative excess.


## Historical interval reconciliation — run #204

The historical quote is now traceable to workflow run #204 (run ID `42177465040`), commit `6efa0028e33181347a33f43d6e04a9d25c1a666e`, artifact `triple-barrier-experiment-report` (artifact ID `13484643171`). Its top-level pooled-model field `top5_minus_universe_net_return_block_bootstrap_95pct` is:

- Decimal lower: `-0.0008981007876277349`
- Decimal upper: `0.0012205701220321479`
- Percentage lower/upper: approximately `-0.08981% / +0.12206%`, which rounds to the quoted `-0.09% to +0.12%`.

The **same artifact's cross-sectional gate-input field** is different: `cross_sectional_experiment.fold_metrics.top5_minus_universe_net_return_block_bootstrap_95pct` has lower `+0.000023856960883227305` and upper `+0.0018135542468718992`. The old gate's lower-bound check therefore returned true for its actual cross-sectional input. This explains why the gate showed a relative-excess pass while the top-level pooled-model interval crossed zero: the report compared two different estimands without making the JSON paths sufficiently prominent. This is not evidence that the gate accepted the quoted top-level crossing-zero interval.

Run #208 confirms the fail-closed behavior on the cross-sectional gate input: its cross-sectional interval lower endpoint is `-0.00007571577683105549`, upper `0.0017711065784943101`, so it crosses zero and the corrected interval check is false. Its top-level pooled-model interval also crosses zero. The code hardening remains valuable because it validates the complete CI object and expected bootstrap method, but the historical root cause is **ambiguous reporting / estimand-path confusion**, not a proven false positive by the old lower-bound comparison.

The two intervals use the same five-day circular moving-block bootstrap mechanics but different daily spread series: pooled-model versus cross-sectional top-five selection. They must never be substituted for one another. No turnover analysis or model promotion follows from this reconciliation; the remaining gate and data-provenance failures continue to require RESEARCH HOLD.
