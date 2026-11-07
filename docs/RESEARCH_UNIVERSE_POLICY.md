# Research universe policy

**Effective decision:** 2026-11-07  
**Status:** SCOPE DECIDED; DATA INTEGRATION BLOCKED; RESEARCH HOLD

## Decision

The research candidate universe is **all eligible NSE-listed ordinary equity securities**, evaluated point-in-time on each signal date. Nifty 500 is a benchmark/reference index, not the historical candidate-universe gate. The prior full point-in-time Nifty 50 scope is superseded as the candidate-universe definition; the existing Nifty 50 archive and reconstruction work are retained as historical reference evidence and may support benchmark or comparison research.

This decision removes dependence on historical Nifty 50/Nifty 500 constituent membership for determining candidate eligibility. It does **not** remove the need to reconstruct what securities were actually listed, eligible, identifiable and tradable at each historical date.

## Eligibility and lifecycle contract

A security may enter the candidate set only when its point-in-time security-master record supports all of the following:

1. NSE listing was effective on the signal date and had not yet been terminated, suspended or otherwise made ineligible.
2. The instrument is an ordinary equity share within the explicitly configured instrument scope. ETFs, debt, preference shares, REITs, InvITs, warrants, rights entitlements and other non-ordinary-equity instruments are excluded unless a separately versioned policy explicitly adds them.
3. The exchange security identity, series, symbol changes, mergers, demergers and successor/predecessor relationships are effective-dated and auditable.
4. Liquidity and data-quality filters use only observations available on or before the signal date. No future market capitalisation, turnover, listing status, index membership or survivorship-derived filter may leak backwards.
5. Required OHLCV, benchmark context, corporate-action and execution-cost inputs meet the applicable evidence gates. Missing or ambiguous records are quarantined or fail closed; they are not silently dropped or imputed.

The exact liquidity thresholds, eligible series, suspension treatment and market-cap/turnover rules are **not yet approved**. They must be pre-registered, versioned and tested before a historical experiment. Do not invent thresholds or backfill missing security history from current constituents.

## Historical completeness and survivorship controls

- Maintain a point-in-time security master with `security_id`, exchange, instrument type, series, symbol, `valid_from`, `valid_to`, listing/delisting/suspension status, source provenance, source publication time, evidence path and SHA-256.
- Preserve delisted, merged, failed and otherwise inactive securities for the periods in which they were listed and eligible. A present-day NSE list is suitable only for a prospective snapshot, not an unbiased historical backtest.
- Keep ticker aliases separate from security identity. A ticker rename is not automatically a new security; a demerger is not automatically a continuous price series.
- Reconcile corporate actions and adjusted-price lineage independently. Never infer a price adjustment factor from an entitlement ratio or a vendor-adjusted price discontinuity.
- Apply filters as-of each signal date and record exclusion reasons, source timestamps and policy version.
- If a historical security master or price history cannot be established, report the coverage gap and keep the affected experiment blocked. Do not substitute current Nifty 500 members or the legacy 49-symbol list.

## Benchmark policy

Nifty 500 may be used as a benchmark/reference series for comparative performance and market context. If a benchmark calculation specifically requires historical Nifty 500 membership (rather than a vendor-provided index return series), reconstruct and verify those historical index constituents separately. Benchmark membership must not determine the broader NSE-listed candidate set.

The existing Nifty 50 notice inventory, transition register and source archive remain useful source material and must not be deleted. Their AI-only classifications remain pending human sign-off and do not become verified because the candidate universe has changed.

## Migration and acceptance sequence

1. Freeze this scope decision and config version; keep `config/universe.txt` explicitly labelled legacy.
2. Design and validate a security-master schema and primary-source acquisition process for listing, delisting, suspension, instrument type, series and identity events.
3. Define and pre-register eligible series, liquidity thresholds, lookback windows, suspension rules and data-quality thresholds without look-ahead.
4. Build a historical listed-security inventory including inactive/delisted names; reconcile primary exchange evidence and source hashes.
5. Reconcile symbol/security identity and corporate-action lineage, including unresolved LTIM/LTM and TATAMOTORS/TMPV/TMCV records.
6. Build a point-in-time OHLCV panel with missing/delisted coverage explicitly reported; validate corporate actions and execution costs.
7. Add tests for listing boundaries, delisting boundaries, symbol continuity, demergers, suspensions, stale/illiquid filters, no-future-data leakage and survivorship inclusion.
8. Only after independent evidence review, register a new universe-specific experiment and run walk-forward evaluation. The existing final holdout remains locked until all prerequisites pass.

## Non-negotiable safety state

This is a scope change only. It does not validate the security master, historical price panel, corporate-action ledger, costs or model. It does not authorize a full-universe experiment, unlock the confirmatory holdout, enable promotion or enable live execution. Keep `RESEARCH_HOLD`, `promotion_eligible=false`, `live_execution_enabled=false` and `LOCKED_NOT_EVALUATED` unchanged.
