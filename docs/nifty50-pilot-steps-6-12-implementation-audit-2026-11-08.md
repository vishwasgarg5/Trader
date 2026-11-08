# Nifty 50 pilot — Steps 6–12 implementation audit

Date: 2026-11-08  
Experiment: `NIFTY50_PILOT_001`  
Audited branch: `main`  
Code/test revision validated: `09fc20c7a84d5c754e6e4df7778c7d60e8866c64`

## Executive result

**Steps 6–12 engineering contracts are implemented and CI-tested at the synthetic/contract level. They are not historically validated and do not authorize historical evaluation.** The upstream evidence chain is still blocked: point-in-time membership is unverified, identity/corporate-action lineage is unresolved, pilot OHLCV and Nifty 50 TRI files are header-only, broker tariffs are not reconciled, the power design's alpha/target-power inputs are not preregistered, factor formulas are not frozen, and no independent reviewer is designated.

## Step-by-step disposition

| Step | Engineering implementation | Validation | Evidence / remaining boundary | Disposition |
|---|---|---|---|---|
| 6 — Fixed-horizon labels | `trader/nifty50_pilot_labels.py`; exact five-session ordinal interval, compounded fixed reference cost, strict >1 pp relative excess, duplicate rejection and unresolved-not-negative behavior. | 12 dedicated synthetic tests; included in full suite. | Historical generation remains disabled until Steps 2–5 are verified and explicitly authorized. | **IMPLEMENTED / SYNTHETIC_TESTED** |
| 7 — Features and events | `trader/nifty50_pilot_controls.py` adds publication/first-seen availability, HTTPS provenance, SHA-256 format checks and per-signal as-of feature snapshots. Existing `trader/events.py` requires announcement dates and records source hashes. | Synthetic tests reject future revisions, bad hashes, non-HTTPS sources and duplicate provenance. | Historical event/feature coverage and publisher timestamps remain unverified. | **IMPLEMENTED / SYNTHETIC_TESTED** |
| 8 — Portfolio | Existing cash-funded simulator, daily mark-to-market diagnostics, five-position limits, sector/gross exposure and execution helpers; Step 8 tests are now included in pilot protocol CI. | Portfolio, diagnostics and pilot execution tests pass in CI. | No historical portfolio result is valid until membership, prices, actions, TRI, costs and fill evidence pass. | **IMPLEMENTED / SYNTHETIC_TESTED** |
| 9 — Power / MDE | `estimate_precision_lift_mde` uses actual date-level five-pick/eligible counts and moving 20-session block resampling; explicit seed, alpha, target power and simulation count are required. MDE above 6 pp returns INCONCLUSIVE. | Deterministic synthetic reproducibility, count validation and insufficient-history tests. | No real qualifying daily observations; alpha and target power are not frozen in the registered protocol. No empirical MDE was run or claimed. | **IMPLEMENTED / SYNTHETIC_TESTED; EMPIRICAL POWER NOT RUN** |
| 10 — Walk-forward | `build_purged_walk_forward_folds` uses an explicit development calendar and actual outcome end dates; enforces the six-session purge. It accepts no holdout dataset. | Synthetic chronology, purge and out-of-calendar rejection tests. | No historical folds or OOS predictions may be generated until data gates pass; final holdout remains locked. | **IMPLEMENTED / SYNTHETIC_TESTED** |
| 11 — Factor / promotion gates | Factor-alpha gate requires the 95% lower bound above zero, frozen definitions/sensitivity, validated data and human review. Sixteen-gate matrix fails closed and encodes no promotion/paper/live authority. | Synthetic missing-gate, missing-review, unfrozen-design and safety tests. | Factor formulas and inference sensitivities are not frozen; no historical factor evidence or independent reviewer exists. | **GATE CODE IMPLEMENTED / SYNTHETIC_TESTED; FACTOR EVALUATION BLOCKED** |
| 12 — Integrity / leakage | Source-manifest schema validation, SHA-256 byte comparison, timestamp/provenance checks, feature availability checks and duplicate detection. | Synthetic matching/mismatching payload and point-in-time leakage tests. | Hash agreement proves byte consistency only, not publisher authenticity or historical truth. Real source coverage and review remain incomplete. | **IMPLEMENTED / SYNTHETIC_TESTED** |

## CI evidence

All checks below ran on code/test revision `09fc20c7a84d5c754e6e4df7778c7d60e8866c64`:

- Python test suite: **302 passed** — [run #42444132754](https://github.com/vishwasgarg5/Trader/actions/runs/42444132754).
- Nifty 50 pilot protocol checks: **success** — [run #42444132760](https://github.com/vishwasgarg5/Trader/actions/runs/42444132760).
- Model Status job: success; automated NSE evidence refresh skipped — [run #42444132830](https://github.com/vishwasgarg5/Trader/actions/runs/42444132830).

The protocol workflow's fail-closed readiness checks correctly preserve the membership and price/TRI blockers. CI success is software-contract validation, not market-data validation or predictive evidence.

## Upstream evidence gates still open

1. **Step 2 — PIT membership:** zero verified historical membership rows/annual coverage; source archive review and independent sign-off incomplete.
2. **Step 3 — identity/corporate actions:** alias rows are unverified; two corporate-action adjustment-factor rows remain unresolved.
3. **Step 4 — OHLCV and TRI:** `data/reference/nifty50_pilot_ohlcv.csv` and `data/reference/nifty50_tri.csv` contain headers only. A legacy 49-symbol price snapshot is not a point-in-time Nifty 50 panel.
4. **Step 5 — execution/costs:** broker tariff/contract-note validation remains outstanding. The single corrected-design Motilal attempt 003 returned `NOT_ACQUIRED`, with zero eligible links and zero downloads. Diagnostics artifact: [attempt 003](https://github.com/vishwasgarg5/Trader/actions/runs/42443486727). The attempt is consumed; no retry or alternate AMC is authorized.
5. **Protocol freeze and review:** pilot config remains `DRAFT_NOT_FROZEN`; power alpha/target power, factor formulas, inference sensitivity, trial census and independent review remain outstanding.
6. **Holdout:** `LOCKED_NOT_EVALUATED`; zero verified annual anchor years and no clean common data span. No dates exist and no access is authorized.

## Branch-cleanup check

The previously named `protocol/final-definition-draft` branch no longer appears in the repository branch listing; the listing currently contains only `main`. Branch cleanup is therefore **confirmed complete**. This is separate from pilot Step 4 market-data readiness, which remains blocked as described above.

## Safety state

- Nifty 50 only; exactly five selections per qualifying date.
- No Nifty 200/500 expansion.
- Holdout locked and unevaluated.
- `evaluation_authorized=false`, `promotion_eligible=false`, `paper_trading_eligible=false`, `live_execution_enabled=false`.
- Pilot GO, if ever reached, means only eligibility for a separately approved broader experiment.

**Conclusion:** The Steps 6–12 software/engineering layer is complete to the synthetic-test boundary. The Nifty 50 pilot itself is not complete, not frozen, not historically evaluable and remains on RESEARCH HOLD.
