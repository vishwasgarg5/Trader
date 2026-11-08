# Nifty 50 TRI source acquisition note

Date: 2026-11-08  
Experiment: `NIFTY50_PILOT_001`  
Branch: `main`

## Acquired series and source route

NSE Indices' historical reports portal is the intended official source route:

- Portal: https://www.niftyindices.com/reports
- Report selector: `Total returns Index Values`
- Index selection: `NIFTY 50`
- Acquired period: 2018-01-01 through 2024-12-31
- Selected series: `Total Returns Index` (gross TRI), not `Net Total Return Index` and not the price-return index.

On 2026-11-08, the repository acquired 1,734 observations through the NSE Indices reverse-engineered endpoint `https://niftyindices.com/BackPage/getTotalReturnIndexString`, using 14 half-year request chunks. Original response bytes are retained under `data/reference/source_documents/nifty50_tri/`; their SHA-256 digests, byte counts, requested ranges and row counts are recorded in `data/reports/nifty50_tri_acquisition.json`. The normalized series is `data/reference/nifty50_tri.csv`.

This endpoint is not a documented stable public API contract. The portal is the official discovery/export route, but the automated endpoint payloads and the exact export semantics have not yet been independently authenticated. Hashes establish local byte integrity, not publisher authenticity or semantic correctness.

## Current structural audit

The structural audit currently reports:

- 1,734 unique, chronologically ordered observations from 2018-01-01 through 2024-12-31.
- 14 raw response files with SHA-256 linkage covering all 1,734 normalized observations.
- Seven weekend-dated observations; each now maps to an archived NSE circular PDF with a recorded SHA-256 digest in `data/reference/nifty50_tri_weekend_session_review.csv` and `data/reports/nifty50_tri_weekend_circular_archive.json`.
- 39 gaps greater than three calendar days are diagnostic flags only; they have not been adjudicated against a complete authoritative exchange calendar.
- Calendar completeness remains `NOT_CERTIFIED_NO_INDEPENDENT_EXCHANGE_CALENDAR`.
- Source authenticity and independent reviewer sign-off remain pending.

The seven weekend circular PDFs passed the download/PDF-signature checks. This does not prove the TRI observation values are correct, nor that all weekday gaps are valid exchange holidays. The circulars still require independent review.

## Pilot-specific selection rule

The registered benchmark is `NIFTY_50_TRI`. Use only the `Total Returns Index` (gross TRI) series. Do not silently substitute:
- the price-return NIFTY 50 close;
- the `Net Total Return Index` column; or
- a third-party reconstructed index series.

If the portal's available series naming or export semantics do not map unambiguously to the registered benchmark, stop and record the discrepancy for protocol review rather than changing the benchmark after seeing results.

## Remaining verification checklist

1. Independently obtain the portal's native CSV export for the exact index and date range, preserve its original bytes, and reconcile its observations against the acquired endpoint series.
2. Record exact report selection, index, requested date range, retrieval timestamp (Asia/Kolkata), and any visible source/version metadata.
3. Compare all session dates with an authoritative NSE cash-market trading calendar for 2018–2024; adjudicate every gap and all special sessions. Do not infer missing sessions from weekdays alone.
4. Independently inspect the seven archived weekend circular PDFs and verify their dates, market segment, session schedule and relevance to each TRI row.
5. Reconcile sample and boundary TRI values against an independently obtained official export; retain all mismatches and do not overwrite evidence silently.
6. Preserve raw bytes and SHA-256 linkage; record reviewer identity and sign-off only when a real independent reviewer completes the work.
7. Keep every row at `ACQUIRED_PENDING_INDEPENDENT_REVIEW` until source, calendar and semantic checks are complete.

## Current status and authorization boundary

The TRI is **ACQUIRED, NOT VERIFIED**. The structural chronology and raw-byte hash checks pass, but calendar completeness, endpoint/source authenticity, native-export reconciliation and independent review are outstanding. This acquisition does not authorize historical labels, walk-forward evaluation, final-holdout access, promotion, paper trading or live execution.

The pilot remains Nifty 50 only, exactly five selections per qualifying date, with Nifty 50 gross TRI as benchmark. No Nifty 200/500 expansion is authorized.
