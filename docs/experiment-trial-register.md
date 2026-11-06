# Experiment trial register

This register is append-only. Add one row before each new model, feature, target, portfolio, threshold or cost-assumption experiment. Do not delete failed or null-result trials. The final holdout is excluded from exploratory trialing and remains locked.

| Trial ID | Date (UTC) | Commit SHA | Artifact / manifest evidence | Hypothesis / single changed dimension | Pre-registered metric and gate | Result artifact | Decision |
|---|---|---|---|---|---|---|---|
| T-0001 | 2026-11-06 | `49e3a2e0d682ae0b3c0122f90e3c86d88db3d7be` | Embedded data snapshot manifest; experiment report SHA-256 `442ec15f8403830ac0c8f852beed76f50630170a93e7740376156b72e95c68a3` | Add rank IC, decile spread and fixed 1/2/5-pick sensitivity; add 30% sector entry cap and 50% sizing after 10% drawdown | Rank IC, HAC t-stat, net decile spread and block-bootstrap CI; fixed 1/2/5-pick sensitivity | [Run #182](https://github.com/vishwasgarg5/Trader/actions/runs/42170299528) | **Completed — research hold.** Cross-sectional top-five net return -0.1371%; 11/16 folds positive excess; excess 95% CI +0.0340% to +0.2116%; model-vs-logistic AUC 95% CI crosses zero; risk-on/low-VIX gate 7/14 folds; PIT membership and corporate-action verification absent. One-pick +0.93% is sensitivity only, not a selected strategy. |

| T-0002 | 2026-11-06 | `8f5abdfcad5c46d13a05f3cf4bb74c57ff88db1c` | #234 report manifest SHA-256 `7f4d889dfa68d17833e4f5a6851116f272926c1ec11cc6fb5d7a100c0ac6eaf7`; price-panel SHA-256 `75fefb8c1a94f1e1f1844b973947531044f92a7fd3bdae6367f08413f45f00b3` | Harden continuation criteria: require absolute net profitability, statistically positive AUC advantage over logistic, passing regime check, point-in-time universe and corporate-action evidence; report sector-cap drift under daily marks | Unit tests plus full walk-forward report; no feature or threshold tuning; final holdout remains locked | [Run #234](https://github.com/vishwasgarg5/Trader/actions/runs/42215010261) | **Completed — STOP / research hold.** 16 folds; cross-sectional top-five mean net return -0.1653%; mean universe -0.2622%; relative excess +0.0950%, 95% CI +0.0052% to +0.1845%; AUC 0.5260 vs logistic 0.5235, paired 95% CI -0.00319 to +0.00746. Gate fails absolute profitability, regime majority, incremental AUC, PIT membership and corporate-action adjustment verification. Mark-to-market portfolio return -43.95%; max realised drawdown 46.82%. Final holdout remains locked. |

## Historical runs requiring reconciliation

| Run | Commit SHA | Evidence status | Treatment |
|---|---|---|---|
| #171 | `06bf56e3cbe826f1194c0b2b893730ea8b7f5bbd` | Previously inspected artifact SHA-256 `e6721cc80b0ae96a1f7d121a4c40a7a2220b3af0c98dcacb0afb4c412f8cb4b6` | Baseline evidence; gates failed |
| #172 | `880d65d6837df53a6a2b1f92fd5ac979d3109401` | Artifact metadata available; contents not reconciled in this register | Do not treat as a distinct independent trial until config/data differences are reconstructed |
| #175 | `8449ef24ae0c791a80a65fddea45b9c9fb3740fa` | Artifact metadata available; contents not reconciled in this register | Do not infer performance from CI success |
| #177 | `46e20f7023473b70475a4f065804be6b6201c34c` | Run was in progress at last inspection | Pending result reconciliation |

The historical experiment count is not yet complete: earlier parameter changes and run-to-run configuration differences must be reconstructed from commits and artifacts. Do not claim a Deflated Sharpe Ratio or multiple-testing correction until the full trial universe, selection process, return series and effective number of independent trials are documented. Future trials must be registered before execution.

## Rules

1. Change one research dimension at a time where practical.
2. Record all tried configurations, including failed and abandoned trials.
3. Freeze commit SHA, data manifest, universe, costs, risk limits, random seeds and evaluation dates.
4. Use walk-forward data only for exploration. Do not inspect final-holdout returns while tuning or debugging.
5. Report dependence-aware intervals; do not promote based on a positive point estimate whose interval includes zero.
6. Any additional feature or threshold experiment after a failed pre-registered gate requires a written rationale and a new trial ID.


## T-0001 interpretation

The model's relative top-five advantage was positive in 11/16 folds and its cross-sectional excess-return bootstrap interval was positive. However, absolute top-five net return was -0.1371%, the model-vs-logistic AUC difference interval included zero, the predeclared risk-on/low-volatility regime check passed only 7/14 evaluable folds, and the data manifest reported no verified point-in-time membership or corporate-action adjustment ledger. The experiment therefore does not establish a deployable edge. The one-pick sensitivity result must not be promoted or tuned against the same walk-forward sample.

## Universe-change record (not a model trial)

| Change ID | Date (UTC) | Commit | Change | Evidence and disposition |
|---|---|---|---|---|
| U-0001 | 2026-11-06 | `48bdea3a0637cabadff86f97669c11414a4a04f9` | Replaced `TATAMOTORS.NS` with `TMPV.NS` in the fixed 49-symbol universe after the NSE symbol/name transition; sector classification and corporate-action ledger were also renamed to TMPV. | **Unverified lineage; quarantine from inferential use pending reconciliation.** The NSE circular establishes the passenger-vehicle symbol change effective 2025-10-24, but the demerger also created a separately listed commercial-vehicle security (TMCV) on 2025-11-12. The 1:1 entitlement is not a price factor. Yahoo's pre-demerger TMPV history, adjusted OHLCV, and the official special-pre-open price discovery have not been reconciled. Do not treat TMPV as a proven continuous single-security series or infer a factor. |

The change above is a universe/data-lineage change, not an independent model trial. Until verified, any experiment containing TMPV history across the 2025-10-14 demerger is not eligible to support performance or promotion claims. A safe keep/drop decision requires checking the exact downloaded TMPV bars and their source lineage; the current evidence is insufficient to keep it as a validated continuous series. Do not silently replace it with TMCV or combine both securities into one series.

## Data-window reconciliation

The daily pipeline calls `download_prices(universe)`, whose default is `period="3y"`; the current integrity report therefore describes roughly 742 rows per symbol. The walk-forward experiment explicitly calls `download_prices(universe, period="7y")`. These are different input windows and must not be described as one shared frozen dataset. The experiment creates its own `data/snapshots/input_manifest.json` after downloading and writing `data/raw/price_panel.csv`; the daily integrity report does not consume that experiment manifest. The #233 artifact is not available while its experiment step is still running. Compare the eventual #233 manifest's price-panel hash, symbol/date coverage, and manifest hash against its report before accepting the gate result. Do not compare daily-model metrics directly with walk-forward metrics.

## Run-to-trial reconciliation queue

Workflow runs are executions, not automatically independent statistical trials. A single pre-registered configuration can produce multiple reruns; conversely, code/configuration changes may create a new trial even when the workflow run is not the only distinguishing feature. The register must map each run to the commit, universe, target, features, costs, evaluation window and manifest before counting independent trials.

| Run | Commit SHA | Current evidence | Reconciliation status |
|---|---|---|---|
| #204 | `6efa0028e33181347a33f43d6e04a9d25c1a666e` | Report artifact inspected in the gate audit; historical pooled and cross-sectional intervals were different estimands. | Reconcile configuration and manifest against T-0001/T-0002; do not count as independent without comparison. |
| #223 | `efcb72dfcc7d7aa9f51bcb551b3ee0a9158ac61f` | Completed successfully; prior report showed negative absolute portfolio return and intervals crossing zero. | Map to registered configuration and compare manifest/return series; no independent-trial claim yet. |
| #233 | `b72c22fd21a2f2049b02c6b24407ca199cdb3625` | In progress at register update; unit tests passed, walk-forward step running, artifact not yet uploaded. | Pending report, manifest and gate verification. |

Runs #171, #172, #175, #177 and #182 remain listed above or under T-0001. The current two trial IDs are not a complete historical trial census. No multiple-testing-adjusted significance claim is permitted until the full configuration/run map is reconstructed.



## #234 report reconciliation (2026-11-06)

Run #233 was cancelled when the register commit superseded its in-progress execution; #234 completed successfully on commit `23987aec4c111bf8eeac5ec94b3cd432edb98983`. Unit tests, the walk-forward experiment and artifact upload all passed. Artifact digest: `sha256:7f4d889dfa68d17833e4f5a6851116f272926c1ec11cc6fb5d7a100c0ac6eaf7`.

The embedded snapshot manifest is tied to run #234 and commit `23987aec4c111bf8eeac5ec94b3cd432edb98983`. It contains 10 hashed inputs, including a seven-year `data/raw/price_panel.csv` (2019-11-06 through 2026-11-06; 49 configured symbols plus Nifty and India VIX) with SHA-256 `75fefb8c1a94f1e1f1844b973947531044f92a7fd3bdae6367f08413f45f00b3`. This confirms the walk-forward artifact's own frozen input snapshot; it does not make it the same dataset as the daily three-year integrity report.

The cross-sectional gate inputs (not the separate pooled-model top-level metrics) were: 16 folds; 11 folds with positive top-five excess; cross-sectional excess mean +0.0950%, 95% five-session circular-block CI +0.0052% to +0.1845%; cross-sectional top-five absolute mean net return -0.1653%; risk-on/low-VIX positive folds 7/14; model-minus-logistic AUC +0.00255, paired 95% CI -0.00319 to +0.00746. Thus the relative-excess sub-gate passes, but the continuation gate correctly returns STOP because absolute net profitability, regime majority, incremental AUC significance, point-in-time membership and corporate-action adjustment verification fail. The pooled-model metrics at the report top level are a separate estimand and must not be substituted for the cross-sectional gate inputs.

The mark-to-market portfolio simulation ended at ₹560,459.58 from ₹1,000,000 (net return -43.95%) with maximum realised-equity drawdown 46.82% across 1,130 trades. The report warns this drawdown is based on realised equity at event dates and understates intra-trade mark-to-market drawdown. This is not a deployment result.

TMPV appears in the frozen seven-year price panel from 2019-11-06, including the 2025-10-14 transition. Its adjusted OHLC series closes at ₹655.31 on 2025-10-13 and ₹392.20 on 2025-10-14, then continues around ₹400. The exact Yahoo adjustment lineage and official special-pre-open adjustment remain unreconciled; both corporate-action adjustment factors remain blank. This confirms that pre-event TMPV data is present, not that it is valid. Keep the TMPV lineage quarantine in force; no performance claim should rely on it until independently reconciled.

The #234 report reports 84,090 labelled rows and 43 ambiguous rows. Delivery coverage is 97.64%. The 30% sector cap is recorded in the portfolio simulation, but its reported peak sector exposure should be checked against daily marked exposures before treating the cap as a proven hard limit.

The separate daily mark-to-market portfolio diagnostic is less severe than the event-date realised-equity trade ledger but still materially negative: ₹1,000,000 to ₹794,701.66 (net -20.53%), maximum daily drawdown 22.81%, 1,180 trades, and 0.45 win rate. The 30% sector limit is an entry-time cap, not a continuously maintained cap: mark-to-market drift exceeded 30% on 100 exposure days, with a maximum observed sector weight of 30.578%. The report explicitly records `entry_only_mark_to_market_drift_is_reported_no_forced_rebalance`; do not describe this as a hard daily exposure ceiling.


## T-0003 — full point-in-time Nifty 50 universe (pre-registered; not yet run)

| Field | Frozen specification |
|---|---|
| Registration baseline | `0d42e76061de6c44efb3f74d8780d15d5752da9e` (registration commit precedes implementation and all experiment execution) |
| Universe decision | Full Nifty 50 constituents on each effective date; reject the custom 49-symbol universe. |
| Candidate source | `aditya-jha/nse-historical-membership`, upstream commit `0786cd9159742f4f2012dcd5f01c1f224b0b019b`; candidate CSV blob SHA `4b762a75376b14b9db6304ef70237270bc8da397`. This is a candidate reconstruction only, not authenticated input. |
| Interval semantics | Half-open `[valid_from, valid_to)`; include on `valid_from`, exclude on `valid_to`; blank `valid_to` is open-ended. No inclusive-end conversion or date shifting. |
| Research window | 2018-04-01 onward only, and only after point-in-time data coverage is validated. No pre-2018 candidate intervals enter the experiment. |
| Announcement / look-ahead | Membership is applied from the published effective date, not announcement date. Each membership fact must have `source_published_at <= valid_from`; a row at decision date t may use only facts effective by t and published by t. Future membership rows must not contribute labels or universe eligibility. |
| Missing / delisted securities | Fail closed for any required constituent/session with missing or unusable price data. No silent constituent skipping, forward fill, or survivorship-based exclusion. If complete coverage cannot be achieved, the affected date/fold is blocked and reported; no model run until a separately pre-registered, externally defensible exclusion policy is approved. |
| Authentication | Independently spot-check 10–15 additions/removals across 2018 onward against official NSE Indices circulars/press releases. Mark only sampled events `SAMPLE_VERIFIED`; this does not certify unsampled rows or the full series. Archive primary documents and SHA-256 hashes before use. |
| Corporate actions | TATAMOTORS/TMPV/TMCV lineage remains quarantined. No synthetic continuity, inferred adjustment factor, or merging of security returns. Any affected constituent/date blocks the relevant data until primary price-series reconciliation is complete. |
| Single changed dimension | Universe definition / membership history only. No feature, target, threshold, cost, model, or portfolio tuning. |
| Pre-registered metrics | Compare walk-forward top-five absolute net return, same-day full-universe baseline, relative excess with circular moving-block 95% CI, fold/regime breakdown, cross-sectional AUC vs logistic paired CI, missing-data coverage, and universe cardinality. Report all failures and null results. |
| Decision rule | Research-only diagnostic. No promotion from relative excess alone. Existing continuation gate remains unchanged; absolute net profitability, regime, AUC, data-integrity, corporate-action and PIT evidence gates remain mandatory. Final holdout stays locked; live execution stays disabled. |
| Execution status | NOT RUN. Do not start walk-forward or promotion workflows until primary-source sample checks, interval-boundary/look-ahead tests, full constituent data coverage, and corporate-action blockers are resolved. |

This registration is intentionally made before implementation and before any performance result from the full point-in-time universe is observed. The candidate source hash is frozen for reproducibility but is not a claim of source authentication.


### T-0003 implementation status (2026-11-06; no research run)

- Full point-in-time Nifty 50 is frozen as the intended universe; the custom 49-name list is not the T-0003 universe.
- The candidate CSV remains pinned to blob SHA `4b762a75376b14b9db6304ef70237270bc8da397`, but is **rejected for direct import pending correction**.
- Preliminary comparison covered 18 constituent transition records across 2018–2024 using official NSE Indices press releases. It found the YESBANK/SHREECEM transition should be effective 2020-03-19, while the candidate CSV uses 2020-03-27 for both interval boundaries; it also uses `LTM` where official circulars use `LTIM`. Details and source links are in `docs/universe-membership-source-audit-2026-11-06.md`.
- The source PDFs are not yet archived and hashed in this repository. The sample is not labelled `SAMPLE_VERIFIED` in the evidence matrix. No candidate rows have been imported.
- Half-open interval semantics are now enforced in the audit/application code. Boundary and future-effective-date regression tests pass in CI run [#42226533050](https://github.com/vishwasgarg5/Trader/actions/runs/42226533050).
- The automatic Triple Barrier run triggered by the earlier code/test commit [#42226373556](https://github.com/vishwasgarg5/Trader/actions/runs/42226373556) failed during test collection on the then-present syntax error; the walk-forward step did not execute. The syntax was corrected and CI subsequently passed.
- The expensive Triple Barrier workflow is now manual-dispatch only. No new T-0003 walk-forward result exists. The separate daily signals workflow [#42226532906](https://github.com/vishwasgarg5/Trader/actions/runs/42226532906) completed successfully on the existing configured 49-symbol daily pipeline; it is not a T-0003 result and must not be interpreted as full-universe evidence.
- **Gate: BLOCKED / NOT RUN** until the official circular PDFs are archived and hashed, the candidate history is corrected for superseding notices and ticker aliases, the full Nifty 50 security universe is enumerated, every required constituent has complete usable price data (including delisted/merged names), and TATAMOTORS/TMPV/TMCV corporate-action lineage is reconciled.
