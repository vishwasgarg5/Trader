# Nifty 50 pilot — security identity readiness (Step 3)

Status: **IN_PROGRESS — evidence not verified**

This step establishes controls for effective-dated identity continuity. It does not certify any current or historical mapping and does not authorize stitching price series.

## Required identity evidence

Every mapping must identify:
- a unique alias record;
- alias and official exchange symbols;
- a stable security identifier (ISIN/security-master key) for verified mappings;
- relation type: same-security ticker rename, vendor alias, or separate security;
- non-overlapping effective dates;
- HTTPS primary-source URL and archived source document with matching SHA-256;
- named independent reviewer and ISO review date for every row marked VERIFIED.

A separate security must retain its own identity. It must not be concatenated into another issuer/security's historical price series.

## Corporate-action boundary

The corporate-action ledger's evidence-integrity result is not proof of adjusted-price correctness. Split, bonus, rights, merger, demerger, dividend and symbol-change treatment must be reconciled against official terms and vendor OHLCV. A missing adjustment factor remains unresolved; it is never silently replaced with 1.

## Current repository state

- `security_symbol_aliases.csv` contains three unverified identity records; none is promoted to VERIFIED by this change.
- LTIM/LTM and Tata Motors/TMPV/TMCV identity distinctions remain subject to archived-source and independent review.
- The corporate-action ledger contains source-note evidence but explicitly does not establish adjusted-price correctness.
- The membership interval ledger is still empty, so Step 2 remains blocked and this step cannot be considered complete.

## Acceptance criteria

1. Verified aliases require stable security identity, source URL, archived evidence and matching digest.
2. Verified aliases require reviewer identity and a valid ISO review date.
3. Same-symbol and separate-security semantics remain distinct.
4. Overlapping mappings to different securities fail closed.
5. Corporate-action evidence validity never implies price adjustment verification.
6. No historical data is fabricated and no price series is stitched solely from ticker similarity.

## Safety

Research-only. No holdout access, evaluation authorization, promotion, paper trading or live execution is enabled.


## Targeted identity reconciliation — 2026-11-07

The two known symbol-confusion cases have been corrected at the **candidate-record level only**. They remain UNVERIFIED because the primary circular bytes/hash and independent review are not fully archived in the ledger.

### LTIM / LTM

- NSE's symbol-change circular states LTIM becomes LTM effective **2026-02-27**: https://nsearchives.nseindia.com/content/circulars/CML72948.pdf
- NSE filings identify the same ISIN, **INE214T01019**, with LTIM before the cutover and LTM after it.
- The alias ledger now starts the LTIM-to-LTM mapping on 2026-02-27. The former 2023-07-13 start date was unsupported and has been removed.
- Historical Nifty 50 events in 2023 and 2024 remain recorded under **LTIM**, not LTM. This rename is after the pilot's 2018–2024 research window.

### TATAMOTORS / TMPV / TMCV

- NSE Listing Circular NSE/CML/70875 says TATAMOTORS changes to TMPV effective **2025-10-24**: https://nsearchives.nseindia.com/corporate/vinodn_16102025185058_CML70875.pdf
- NSE filings identify TMPV with ISIN **INE155A01022**.
- NSE identifies TMCV as a separate listed commercial-vehicle security, ISIN **INE1TAE01010**, listed from **2025-11-12**: https://www.nseindia.com/get-quote/equity/TMCV/Tata-Motors
- The alias ledger now records TATAMOTORS → TMPV as the same-security rename and TMCV as a separate security with a different ISIN. The three tickers must not be stitched into one security series.
- These changes are post-2024 and do not create a new constituent or corporate-action row inside the pilot's 2018–2024 sample.

### Corporate-action treatment

Tata Motors' shareholder communication states a 1:1 share entitlement for the demerged commercial-vehicle business, a 2025-10-14 record date, and that the listed entity's share price would be adjusted through a stock-exchange price-discovery mechanism: https://links.sgx.com/FileOpen/NSEBSESHAREHOLDERINTIMATION.ashx?App=Announcement&FileID=863553

The 1:1 share entitlement is **not itself an OHLCV adjustment factor**. No factor has been inferred from the ratio. The demerger event is outside the pilot's 2018–2024 window; the ledger factor remains blank and price adjustment remains unverified. The separate symbol rename is an identity event, not a corporate-action price factor.

No mapping has been promoted to VERIFIED. Source archive bytes/hashes, vendor history reconciliation and independent review remain open.
