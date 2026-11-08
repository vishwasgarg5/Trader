# Nifty 50 TRI source acquisition note

Date: 2026-11-08  
Experiment: `NIFTY50_PILOT_001`  
Branch: `main`

## Verified official source route

NSE Indices publishes a public Historical Data Reports page:

- Portal: https://www.niftyindices.com/reports
- Report selector: `Total returns Index Values`
- Index selection: `NIFTY 50`
- Required date range for the pilot's initial development window: 2018-01-01 through 2024-12-31, subject to verified clean-span and calendar coverage.
- The portal's displayed export schema includes `IndexName`, `Date`, `Total Returns Index`, and `Net Total Return Index`.

The portal page was inspected on 2026-11-08. Its report selector and CSV export are visible, but no index/date selection was submitted in this audit. **No CSV was downloaded, no daily observations were imported, and no completeness or integrity claim is made.**

## Pilot-specific selection rule

The registered benchmark is `NIFTY_50_TRI`. Use the portal's `Total Returns Index` series for that benchmark. Do not silently substitute:
- the price-return NIFTY 50 close;
- the `Net Total Return Index` column; or
- a third-party reconstructed index series.

If the portal's available series naming or export semantics do not map unambiguously to the registered benchmark, stop and record the discrepancy for protocol review rather than changing the benchmark after seeing results.

## Acquisition and evidence checklist

When the export is obtained through the official portal:

1. Preserve the original CSV bytes unchanged before parsing.
2. Record the exact portal URL, selected report, selected index, requested date range, retrieval timestamp (Asia/Kolkata), and any visible source/version metadata.
3. Compute SHA-256 over the original bytes before parsing.
4. Validate unique, strictly increasing trading dates; numeric finite index values; no unexplained gaps against the official NSE trading calendar; and coverage across the full requested range.
5. Preserve the original CSV separately from normalized `data/reference/nifty50_tri.csv`.
6. Populate normalized rows only with the verified TR column and attach source URL, source publication metadata if available, evidence path, SHA-256, verification status, and independent reviewer fields.
7. Keep the pilot fail-closed until independent source and completeness review is recorded.

## Current repository state and boundary

At the time of this note, `data/reference/nifty50_tri.csv` is header-only. The official portal route is now identified, but the TRI data gate remains **NOT VERIFIED**. This discovery does not authorize historical labels, walk-forward evaluation, final-holdout access, promotion, paper trading, or live execution.

The pilot remains Nifty 50 only, exactly five selections per qualifying date, with Nifty 50 TRI as benchmark. No Nifty 200/500 expansion is authorized.
