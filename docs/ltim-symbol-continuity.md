# LTIM / LTM security identity and vendor-history controls

## Official exchange symbol timeline

- The 2023-07-04 NSE Indices Nifty 50 notice names the constituent as `LTIM`; its inclusion was effective 2023-07-13. The 2024-08-23 Nifty 50 review notice also names `LTIM`; its exclusion was effective 2024-09-30. The transition register therefore correctly records `LTIM` for both historical events.
- NSE Listing Circular NSE/CML/72948 (Circular Ref. 0300/2026), dated 2026-02-23, states that LTIMindtree Limited's symbol changes from `LTIM` to `LTM` effective 2026-02-27. This is a same-security ticker rename, not a new constituent or a Nifty 50 membership change.
- An official NSE integrated filing dated 2025-07-17 lists the company's ISIN as `INE214T01019` and its then-current symbol as `LTIM`. The company's 2026-02-27 intimation also confirms that the trading symbol changed from `LTIM` to `LTM` effective that day.

## Corrected identity interpretation

- `LTIM` is the official symbol for the 2023-07-13 through 2026-02-26 interval.
- `LTM` is the official symbol from 2026-02-27 onward for the same LTIMindtree security.
- The prior ledger hypothesis that `LTM` was a vendor alias for `LTIM` beginning 2023-07-13 is not supported by the official exchange timeline and has been replaced by the effective-dated same-security rename record.
- Do not rewrite the 2023 or 2024 Nifty 50 membership events to `LTM`; they remain `LTIM`.

## Vendor-series gate remains open

The official rename establishes the exchange symbol timeline, but it does not prove how a market-data vendor labels or backfills historical bars. Before any price-series splice or alias is accepted:

1. Query both `LTIM.NS` and `LTM.NS` from the same vendor across the pre- and post-2026-02-27 periods.
2. Record each ticker's first/last date, missing sessions, duplicate sessions, OHLCV overlap and corporate-action treatment.
3. Compare overlapping bars and stable security identifiers. Do not infer equivalence from matching company names or from the exchange rename alone.
4. Preserve missing history as a gap; do not silently substitute one ticker or concatenate unverified adjusted-price series.

The alias row remains `UNVERIFIED`; independent review and direct vendor-history reconciliation are still required. This note does not establish price continuity or authorise model promotion.

## Primary sources

- NSE Listing Circular NSE/CML/72948 (2026-02-23): https://nsearchives.nseindia.com/content/circulars/CML72948.pdf
- NSE integrated filing (2025-07-17; ISIN INE214T01019 and then-current symbol LTIM): https://nsearchives.nseindia.com/corporate/ixbrl/INTEGRATED_FILING_INDAS_103616_17072025170520_iXBRL_WEB.html
- LTIMindtree company intimation (2026-02-27): https://nsearchives.nseindia.com/corporate/LTI_27022026084622_Changeinstocktickersigned.pdf
- NSE Indices Nifty 50 inclusion notice (2023-07-04): https://www.niftyindices.com/Press_Release/ind_prs04072023.pdf
- NSE Indices Nifty 50 review notice (2024-08-23): https://www.niftyindices.com/Press_Release/ind_prs23082024.pdf
