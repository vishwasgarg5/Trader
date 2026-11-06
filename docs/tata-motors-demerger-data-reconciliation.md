# Tata Motors 2025 demerger: data reconciliation status

## Source-backed facts

- Tata Motors' composite scheme became effective on 1 October 2025; the appointed date was 1 July 2025.
- The record date for the commercial-vehicle share entitlement was 14 October 2025. Eligible holders received one TML Commercial Vehicles Limited share per existing Tata Motors share.
- The NSE listing circular dated 16 October 2025 states that the existing TATAMOTORS symbol/name changed to TMPV / Tata Motors Passenger Vehicles Limited effective 24 October 2025.
- Tata Group's listing announcement reports that the commercial-vehicle entity listed on 12 November 2025.

Primary-source links:
- Tata Motors shareholder communication (9 October 2025): https://links.sgx.com/FileOpen/NSEBSESHAREHOLDERINTIMATION.ashx?App=Announcement&FileID=863553
- NSE Listing Circular 2041/2025 (16 October 2025): https://nsearchives.nseindia.com/corporate/vinodn_16102025185058_CML70875.pdf
- Tata Group commercial-vehicle listing announcement: https://www.tata.com/newsroom/business/tata-motors-commercial-vehicles-listing

## What this establishes — and what it does not

The passenger-vehicle lineage is TATAMOTORS -> TMPV. The demerger also created a separately listed commercial-vehicle security with a 1:1 share entitlement. Therefore, replacing the configured TATAMOTORS.NS history with TMPV.NS alone would omit the commercial-vehicle entitlement and is not an acceptable total-return reconstruction.

The CSV ledger records the known entitlement date and symbol transition. Its `adjustment_factor=1.0` values are unit share-entitlement/continuity markers only; they are **not** price-adjustment factors and must not be applied to OHLCV.

The two accompanying `*_source_note.txt` files are locally recorded summaries with source URLs and SHA-256 checksums. They are **not the original exchange/company PDFs**. The ledger can therefore establish traceable source-note integrity, but it does not independently verify source-file authenticity or price adjustment.

## Remaining blockers

1. Archive the original signed/official exchange and company documents in this repository and replace the source-note evidence paths with their original-file paths and checksums.
2. Obtain the official special pre-open price-discovery result and a validated historical OHLCV lineage for both TMPV and TMCV.
3. Reconstruct total shareholder value across the unlisted interval from entitlement/allotment through TMCV listing, including correct treatment of the two resulting securities.
4. Reconcile vendor adjusted and unadjusted OHLCV to the official action terms before removing the fail-closed data guard.

Until these are complete, do not substitute TMPV for TATAMOTORS in the fixed 49-symbol universe, do not claim corporate-action-adjusted price history is verified, and keep model promotion and live execution disabled.
