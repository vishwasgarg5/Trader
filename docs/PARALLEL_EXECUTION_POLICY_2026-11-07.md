# Parallel execution policy while Step 2 is on hold

Date: 2026-11-07  
Branch: `main`  
Experiment: `NIFTY50_PILOT_001`

## Decision

Step 2 (point-in-time Nifty 50 membership evidence) is placed on **HOLD / OPEN** while independent engineering work proceeds on the other steps. This is a sequencing decision, not a waiver of Step 2 and not a claim that historical accuracy is unaffected.

The pilot remains Nifty 50 only, with exactly five selections per qualifying date and Nifty 50 TRI as benchmark. No Nifty 200/500 expansion is authorized. Pilot GO, if ever reached, means eligibility for a separately approved broader experiment only; it does not authorize promotion, paper trading, holdout access or live execution.

## Non-negotiable interpretation

- Engineering completion is not data validation.
- Unit tests and CI success are not evidence of predictive edge.
- No historical performance, accuracy, profitability or promotion claim may use current constituents as a substitute for point-in-time membership.
- No point-in-time membership interval, transition verification or human sign-off may be fabricated or inferred from the fact that other work is complete.
- All historical universe-dependent evaluation remains blocked until Step 2 is independently resolved.
- Preserve the research hold, locked holdout, `promotion_eligible=false`, and `live_execution_enabled=false`.

## Work allowed in parallel

| Step | Work allowed now | What remains blocked |
|---|---|---|
| 1. Protocol | Maintain the registered protocol and freeze changes through the required review process. | Final freeze if outstanding preregistration items remain. |
| 2. PIT membership | HOLD. Preserve source inventory, transition register and AMC acquisition protocol without weakening evidence rules. | Membership intervals, full historical universe certification and Step 2 completion. |
| 3. Identity and corporate actions | Implement ISIN syntax/check-digit validation, schema checks, alias/corporate-action audits and deterministic adjustment interfaces. | Marking aliases/actions verified; price-series lineage and total-return certification. |
| 4. OHLCV and Nifty 50 TRI | Improve acquisition, schema, provenance, gap, duplicate, calendar and quality checks. | Claiming a valid historical Nifty 50 panel or benchmark series while membership and source evidence are unresolved. |
| 5. Execution and costs | Test tariff arithmetic, order sizing, slippage scenarios, liquidity caps, partial fills and cost sensitivity. | Broker tariff sign-off from contract notes and verified historical liquidity/execution inputs. |
| 6. Labels | Maintain and test fixed-horizon label code, unresolved-row handling and exact interval semantics. | Enabling historical label generation before membership, identity, total-return, TRI and costs are verified. |
| 7. Features and events | Build typed event schemas, timestamp/leakage controls, feature definitions and synthetic tests. | Historical event feature use until source coverage and point-in-time timestamps are defensible. |
| 8. Portfolio | Extend simulator and diagnostics with synthetic fixtures, cash, partial-fill, exposure, cost and corporate-action accounting tests. | Historical performance claims using unverified universe/price/action data. |
| 9. Power/MDE | Implement and test simulation design, dependence-preserving resampling and preregistered reporting. | Final empirical power conclusion until qualifying clean observations and selection counts exist. |
| 10. Walk-forward | Build deterministic chronological split/purge orchestration and leakage tests. | Running or reporting confirmatory historical evaluation before upstream data gates pass. |
| 11. Factor/promotion gates | Implement gate evaluation and evidence binding; test fail-closed behavior. | Passing any gate on absent, synthetic or unverified evidence. |
| 12. Integrity/leakage | Add schema, hash, point-in-time, duplicate, interval, and leakage regression tests. | Declaring full integrity coverage until real data paths are exercised. |
| 13. Final decision | Maintain decision log and prepare a reproducible final report template. | Final GO/NO-GO, holdout access, promotion or paper-trading authorization. |

## Dependency policy

Every artifact and report must distinguish:
1. `IMPLEMENTED`: code or schema exists and is covered by tests;
2. `SYNTHETIC_TESTED`: behavior is tested only with synthetic fixtures;
3. `SOURCE_ACQUIRED`: original source bytes are stored with provenance and hash;
4. `DATA_VALIDATED`: content and identity have been reconciled against independent evidence;
5. `HUMAN_REVIEWED`: an identified independent reviewer has recorded review and date;
6. `EVALUATION_ELIGIBLE`: every upstream gate required by the protocol is satisfied.

A status may advance only when its own evidence exists. Do not collapse these states into a single "complete" label.

## First parallel implementation checkpoint

The first Step 3 code change adds ISO 6166 ISIN shape and Luhn check-digit validation to the effective-dated alias ledger audit, with matching schema declaration and regression tests. It is an integrity check only: it does not verify any current alias row, establish a security master, or certify adjusted prices.

Existing Step 5 cost calculations, Step 6 fixed-horizon label contract, and Step 8 portfolio simulator may be extended and tested independently. The current corporate-action ledger still contains unresolved TMPV terms, the pilot OHLCV/TRI files remain empty/header-only, and the generic event ledger has no historical observations. These limitations must remain visible.

## Release status

Step 2 remains **HOLD / OPEN**. The complete pilot remains **RESEARCH HOLD**. No historical accuracy claim is authorized by this parallel-work policy.
