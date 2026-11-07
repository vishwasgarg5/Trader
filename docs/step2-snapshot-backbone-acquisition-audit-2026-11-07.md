# Step 2 snapshot-backbone acquisition audit

Audit date: 2026-11-07  
Repository branch: `main`  
Base commit: `376523d6f44dbeb1a0ac288baa045cf51c112908`

## Result

**Snapshot backbone: BLOCKED — no authenticated historical constituent snapshots have yet been acquired into the repository.**

This is an evidence-acquisition result, not a software defect. No membership intervals have been inferred or written.

## Official publisher sources located

1. NSE Indices flagship NIFTY 50 page:  
   https://www.niftyindices.com/indices/equity/broad-based-indices/nifty--50  
   The page exposes an `Index Constituent` download. This is the current constituent endpoint and cannot, by itself, establish the constituent set on a historical date in 2018–2024.

2. NSE India NIFTY 50 page:  
   https://www.nseindia.com/static/products-services/indices-nifty50-index  
   The page exposes the current official Nifty 50 constituent CSV at:  
   https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv  
   The page states it was updated on 2026-10-28. The browser retrieval path did not return the CSV bytes in this audit; no rows or hash are claimed.

3. NSE Indices monthly reports:  
   https://www.niftyindices.com/reports/monthly-reports  
   The official interface lists date-selectable reports including `Market Capitalisation, Weightage, Beta for NIFTY 50 & NIFTY Next 50` and `Indices - Market Capitalisation & Weightage`. These are promising official snapshot candidates, but the audit did not obtain dated 2018–2024 report files or their hashes.

4. NSE All Reports historical archive:  
   https://www.nseindia.com/all-reports  
   The historical reports interface includes date-selectable index reports and daily snapshot report types. The page establishes an official retrieval route, not that any historical snapshot has been downloaded or reconciled.

## Repository evidence inspected

- `data/reference/nifty50_membership.csv` contains only its header: **0 membership intervals**.
- `data/reference/nifty50_transition_register.csv` contains **34 rows**. All 34 have `verification_status=SAMPLE_ONLY`; source URLs and recorded source hashes are populated, but the rows do not carry independent reviewer identity/date.
- `data/reference/nifty50_special_membership_events.csv` contains the three JIOFIN phases (dummy add, replacement by listed JIOFIN, removal). All three remain `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`. The temporary 51-member period must remain a documented special-event exception to the ordinary 50-member invariant.
- `data/reference/nifty50_annual_coverage.csv` has seven years (2018–2024), all `NOT_STARTED`; official notice search, supersession review, snapshot reconciliation and independent reviewer fields are incomplete.
- `data/reference/nifty50_annual_notice_inventory.csv` contains 687 records: 567 `DISCOVERED_UNREVIEWED`, 100 `SCREENED_NO_NIFTY50_CHANGE`, and 20 `CANDIDATE`. The 100 AI screens are not human approvals.
- `data/reference/nifty50_notice_review_queue.csv` contains 108 rows, all `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`.

## Snapshot acquisition protocol

Do not use the current constituent CSV as a historical snapshot. For each selected anchor date, retrieve an official dated NIFTY 50 constituent/market-capitalisation-and-weightage report from the NSE/NSE Indices date-selectable archive. Preserve:

- exact requested as-of date and report name;
- original download URL and retrieval timestamp;
- unmodified response bytes;
- SHA-256 digest;
- parsed symbol/issuer/ISIN rows and parser version;
- source-to-parsed row count and duplicate checks.

Acquire at minimum:
- the latest official snapshot at or before the pilot's 2024-12-31 end date;
- dated snapshots immediately around each effective-date transition in the 2018–2024 register;
- year-end or nearest available official dated snapshots for each year 2018–2024;
- additional snapshots around any unexplained count discrepancy or JIOFIN special-event boundary.

Then replay the transition ledger backward from the latest authenticated anchor. For each effective date, apply all same-date adds/removes as a single event batch and reconcile the resulting set to the closest official dated snapshot. Test set equality, not just row count. Require 50 ordinary constituents; preserve the documented JIOFIN temporary 51-member phase with its distinct dummy/listed identity and price-treatment rules.

A count of 50 alone is necessary but not sufficient: a wrong set can also contain 50 names. Every mismatch must be resolved against official notices, superseding/deferment chains, security identity and the dated snapshot itself.

## Current disposition and next action

No snapshot file was downloaded in this audit, so there is no defensible current-list anchor, no backward replay, no effective-date snapshot reconciliation, and no basis to populate `nifty50_membership.csv`.

The next evidence action is to retrieve and archive the official dated NIFTY 50 market-capitalisation/weightage reports through the NSE/NSE Indices date-selectable report interface, beginning with the 2024-12-31 (or nearest available trading-date) anchor and then the transition dates. If those report downloads are unavailable through the public interface, obtain the dated constituent snapshots directly from NSE Indices and record the access route and any licensing/availability constraint.

**Step 2 remains OPEN / NOT COMPLETE.** Independent human review is mandatory; AI-assisted triage and this acquisition audit are not sign-off. Research hold, holdout lock and all paper/live trading prohibitions remain unchanged.
