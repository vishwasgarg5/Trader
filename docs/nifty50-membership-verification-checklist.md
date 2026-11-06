# Full point-in-time Nifty 50 membership verification

**Scope:** Nifty 50 constituent changes effective from 2018-04-01 through 2024-12-31. T-0003 remains frozen. This document is an execution protocol, not evidence that the history is complete.

## Non-negotiable rules

- Universe on date *t* is the complete official Nifty 50 membership effective on *t*, not the current 49-name configuration.
- Membership intervals are half-open: `[valid_from, valid_to)`. An addition is eligible on its effective date; a removal is ineligible on its effective date.
- Preserve announcement/publication timestamp separately from effective date. A later-published notice cannot establish eligibility at an earlier date unless the notice explicitly makes that date effective and the point-in-time research policy permits the known-at-time distinction.
- Use the latest controlling NSE Indices notice. Search for amendments, acceleration, deferral, cancellation, replacement, merger, delisting and symbol corrections after the first announcement.
- Never infer membership from current constituents, vendor ticker coverage, a third-party CSV, or a surviving security's price history.
- Every source document must be archived byte-for-byte under `data/reference/nse_membership/`, with its canonical source URL, publication date, local relative path and SHA-256.
- A sample check is always `SAMPLE_ONLY`; it cannot satisfy annual completeness.
- Unresolved, unavailable or ambiguous evidence remains blocked. No silent row drops, date interpolation or imputation.

## Verification procedure — every event

1. Enumerate every Nifty 50 review/change event from official NSE Indices notices for the scoped period. Include additions and removals as separate transition rows.
2. Search the notice history for later notices referring to the same review/event. Record the controlling notice and every superseded notice; explain why the controlling notice wins.
3. Extract the exact security name, official symbol, action and effective date. Record publication timestamp separately.
4. Reconcile the candidate history's old and new interval boundaries. Record each mismatch; do not patch from the candidate source without primary evidence.
5. Download the original official PDF, retain the original filename where possible, and compute SHA-256 over the archived bytes.
6. Independently review the extracted details against the PDF. Record reviewer, review date and concise notes.
7. Mark an event `VERIFIED` only when the controlling notice is archived, its digest matches, all supersession links are resolved, and the event fields match the notice.
8. Reconcile the complete event ledger against year-end and effective-date constituent snapshots. Every effective-date snapshot must contain exactly 50 distinct securities unless an official index methodology notice documents an exceptional temporary state.

## Annual completeness gate

The annual coverage register must contain one row for every year 2018–2024. A year can be `COMPLETE` only when:
- the official notice search has been completed for the full calendar year;
- the complete event inventory and its expected count are recorded;
- every event in that inventory has a corresponding verified transition row;
- verified count equals expected count;
- superseding-notice review is complete; and
- independent reviewer sign-off is recorded.

An empty event list is not evidence of zero transitions. It requires an explicit documented search and sign-off.

## Symbol and corporate-action reconciliation

Use `data/reference/security_symbol_aliases.csv` as an effective-dated security identity ledger. Distinguish:
- `TICKER_RENAME_SAME_SECURITY`: same legal security, exchange ticker changed;
- `VENDOR_ALIAS`: vendor-specific ticker spelling mapped to the official security symbol;
- `SEPARATE_SECURITY`: a new security or demerged entity; never concatenate it as a ticker alias.

The LTIM/LTM candidate discrepancy remains unverified pending primary source and vendor-symbol evidence. TATAMOTORS→TMPV is a ticker/name transition for the passenger-vehicle entity effective 2025-10-24, but it does not resolve the demerger's total-return treatment. TMCV is a separate security, not an alias for TMPV. No adjustment factor may be inferred from the 1:1 entitlement ratio.

## Release gates

The full-universe price-panel build is blocked until all seven annual coverage rows are complete, all transition rows pass the evidence validator, all symbol identity conflicts are resolved, and the separate Tata Motors/TMPV/TMCV corporate-action gate is independently cleared.

The model/backtest gate remains closed until the full historical price panel also demonstrates complete constituent coverage, including delisted and merged securities. CI success validates code only; it does not authenticate the historical facts.
