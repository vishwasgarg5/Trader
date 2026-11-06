# Tata Motors symbol continuity and demerger handling

## Exchange symbol transition

NSE Listing Circular 2041/2025 (Download Ref. NSE/CML/70875), dated 2025-10-16, states that the existing symbol `TATAMOTORS` changes to `TMPV` effective 2025-10-24. The company name changes from Tata Motors Limited to Tata Motors Passenger Vehicles Limited. The research universe therefore uses Yahoo Finance symbol `TMPV.NS` for the continuing passenger-vehicle entity.

Official circular: https://nsearchives.nseindia.com/content/circulars/CML70875.pdf

## Demerger is not a simple ticker rename

The 2025 composite scheme separated the commercial-vehicle undertaking into a distinct resulting company. Eligible shareholders received one resulting-company share for each existing share. The shareholder communication states that the old share price was adjusted through an exchange price-discovery mechanism. The 1:1 share-entitlement ratio is not an OHLCV adjustment factor.

Official shareholder communication: https://links.sgx.com/FileOpen/NSEBSESHAREHOLDERINTIMATION.ashx?App=Announcement&FileID=863553

## Research safeguards

- `TMPV.NS` represents the continuing passenger-vehicle/JLR/EV entity formerly quoted as `TATAMOTORS`.
- The commercial-vehicle resulting company is a separate security, not a replacement alias for `TMPV.NS`.
- Do not splice the two securities into one price series.
- Do not infer a demerger price-adjustment factor from the 1:1 share-entitlement ratio.
- Yahoo Finance `auto_adjust=True` is not accepted as independent proof that this demerger and all other corporate actions are correctly reflected.
- The data-integrity and promotion gates remain closed until the downloaded history, official exchange price-discovery values, and vendor adjusted OHLCV are reconciled.
- The configured universe remains a static research snapshot; this update does not establish point-in-time index membership.

This document records source facts and explicit limitations. It does not certify adjusted-price continuity or authorise promotion.
