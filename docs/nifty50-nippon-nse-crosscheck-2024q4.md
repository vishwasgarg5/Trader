# Nippon 2024-Q4 portfolio cross-check

The official Nippon India monthly portfolio workbook for 2024-12-31 contains a dedicated scheme sheet identified from the workbook INDEX as `NIPPON INDIA INDEX FUND - NIFTY 50 PLAN`. The sheet reports 50 listed equity rows with 50 distinct valid ISINs. Its workbook SHA-256 is `cedbc87fc0dd68019a7eb95d072064b2fbb438a5dddeb95c138f3e63d7e452b8`.

A bounded workflow now:
1. Downloads that workbook from the official AMC URL and parses only the exact Nifty 50 scheme sheet.
2. Downloads the NSE CM bhavcopy for 2024-12-31 and maps ISIN to symbol using EQ-series rows.
3. Compares the resulting 50 symbols to the CDX-verified 2024-Q4 Wayback anchor captured 2024-11-10.
4. Lists intervening transition-register events and preserves their current verification status.

This is a checkpoint comparison only. A match is not a canonical membership decision, and a mismatch is a review item. No ledger or model input is modified.
