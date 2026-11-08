# NIFTY 50 Wayback snapshot pair-diff audit — 2026-11-08

## Purpose and evidence boundary

This is a machine-generated candidate-difference audit of the downloaded Wayback constituent CSV snapshots currently committed on this research branch. The snapshots are supplementary archival evidence, not authenticated point-in-time membership decisions. Each observed difference is a candidate event with a broad date window; it must be reconciled against the supersession-checked NSE Indices notice chain and corroborating evidence before any transition is verified.

No canonical membership ledger, model, holdout, or trading state is modified by this report.

## Snapshot inventory

All nine captures below validated as 50 rows, 50 distinct symbols, 50 distinct ISINs, with no duplicate symbols and no missing ISINs. The 2021-06-15 and 2021-09-03 captures have identical raw-byte SHA-256 values and therefore identical constituent sets.

| Capture timestamp (UTC) | Quarter | Original URL host/path | Local SHA-256 | Validation |
|---|---|---|---|---|
| 2021-06-15 18:35:23 | 2021-Q2 | niftyindices.com/IndexConstituent/ind_nifty50list.csv | `ebf5372eba6be1318abe3d6b143af2280bb8d996b41bee7ee8d8c7b47912f646` | 50/50 symbols and ISINs |
| 2021-09-03 11:31:22 | 2021-Q3 | archives.nseindia.com/content/indices/ind_nifty50list.csv | `ebf5372eba6be1318abe3d6b143af2280bb8d996b41bee7ee8d8c7b47912f646` | 50/50; byte-identical to 2021-06 |
| 2022-07-28 03:41:49 | 2022-Q3 | niftyindices.com/IndexConstituent/ind_nifty50list.csv | `4f4435c0f0ea12a5f09711afc755d246092aa9f6848d83b492db1f9a00138044` | 50/50 |
| 2023-01-26 06:02:50 | 2023-Q1 | archives.nseindia.com/content/indices/ind_nifty50list.csv | `6291c898e93077ba72aa42e9b10c8a49ea259a3c541ed98f24445f36ece16397` | 50/50 |
| 2023-05-22 05:12:28 | 2023-Q2 | archives.nseindia.com/content/indices/ind_nifty50list.csv | `6291c898e93077ba72aa42e9b10c8a49ea259a3c541ed98f24445f36ece16397` | 50/50; byte-identical to 2023-01 |
| 2024-02-05 22:28:33 | 2024-Q1 | archives.nseindia.com/content/indices/ind_nifty50list.csv | `c28d945bb2e23ad7a3ae4f8e1319010c9796d252de07aefed5d93f53112d03ba` | 50/50 |
| 2024-05-24 07:38:05 | 2024-Q2 | niftyindices.com/IndexConstituent/ind_nifty50list.csv | `04e18d679f517fcad1eae56b80c97f45616f78214e5ab517b28254de72e2c51f` | 50/50 |
| 2024-08-19 18:45:01 | 2024-Q3 | nsearchives.nseindia.com/content/indices/ind_nifty50list.csv | `9fb8832853c279448d2bc05f0e7dd5f460ed2ff35332fea8c40fc1250362ad28` | 50/50 |
| 2024-11-10 01:37:17 | 2024-Q4 | niftyindices.com/IndexConstituent/ind_nifty50list.csv | `222a52f838bff623244be25592931e9b064a1375ac2fbc0ba23241aab25a0db5` | 50/50 |

Note: this inventory has nine capture timestamps across the eight lines? The first two 2021 captures and the two 2023 captures are separately retained; all rows above are distinct captures. The local SHA-256 is the hash of the downloaded raw bytes. The CDX digest is a separate Wayback metadata field and is not substituted for the local hash.

## Consecutive symbol-set differences

The comparison key here is the listed trading symbol. A symbol leaving/entering the CSV is only a candidate set difference between two capture dates, not proof of the effective date or a formal index committee decision.

### 2021-06-15 → 2021-09-03

No symbol-set difference. The raw-byte hashes are identical.

### 2021-09-03 → 2022-07-28

- Symbol out: IOC (Indian Oil Corporation Ltd.)
- Symbol in: APOLLOHOSP (Apollo Hospitals Enterprise Ltd.)
- Candidate date window: after 2021-09-03 and on/before 2022-07-28.

### 2022-07-28 → 2023-01-26

- Symbol out: SHREECEM (Shree Cement Ltd.)
- Symbol in: ADANIENT (Adani Enterprises Ltd.)
- Candidate date window: after 2022-07-28 and on/before 2023-01-26.
- BAJAJFINSV and TATASTEEL retain the same symbols/company names but show changed ISINs between these files. Treat these as security-identity/ISIN changes for investigation, not constituent additions/removals.

### 2023-01-26 → 2023-05-22

No symbol-set difference. The raw-byte hashes are identical.

### 2023-05-22 → 2024-02-05

- Symbol out: HDFC (Housing Development Finance Corporation Ltd.)
- Symbol in: LTIM (LTIMindtree Ltd.)
- Candidate date window: after 2023-05-22 and on/before 2024-02-05.
- NESTLEIND retains its symbol/company name but shows a changed ISIN. Treat separately from membership.

### 2024-02-05 → 2024-05-24

- Symbol out: UPL (UPL Ltd.)
- Symbol in: SHRIRAMFIN (Shriram Finance Ltd.)
- Candidate date window: after 2024-02-05 and on/before 2024-05-24.

### 2024-05-24 → 2024-08-19

Seven symbol exits and seven entries are visible:

- Symbols out: BPCL, BRITANNIA, DIVISLAB, HEROMOTOCO, INDUSINDBK, LTIM, TATAMOTORS.
- Symbols in: BEL, ETERNAL, INDIGO, JIOFIN, MAXHEALTH, TMPV, TRENT.
- Candidate date window: after 2024-05-24 and on/before 2024-08-19.
- TATAMOTORS → TMPV carries the same ISIN `INE155A01022` across the two snapshots; do not count this alone as a security-level membership change.
- BAJFINANCE, DRREDDY, KOTAKBANK and SHRIRAMFIN retain symbols/company names but have changed ISINs. Resolve corporate/security identity before any transition inference.

### 2024-08-19 → 2024-11-10

Five symbol exits and five entries are visible:

- Symbols out: ETERNAL, INDIGO, JIOFIN, MAXHEALTH, TMPV.
- Symbols in: BPCL, BRITANNIA, HEROMOTOCO, INDUSINDBK, TATAMOTORS.
- Candidate date window: after 2024-08-19 and on/before 2024-11-10.
- TATAMOTORS reappears with the same ISIN `INE155A01022` that was listed as TMPV in the preceding snapshot. Treat the symbol/name reversal as an identity-mapping review item, not automatically as a membership removal/addition.
- BAJFINANCE, KOTAKBANK and SHRIRAMFIN show ISIN changes back to the identifiers in the 2024-05 snapshot; preserve as identity-resolution items.

## Review queue / next machine-assisted matching

1. Reconcile each symbol-set candidate above to the original NSE Indices notice chain and exact effective date; retain broad snapshot windows until narrowed by primary evidence.
2. Match ISIN-only changes (BAJAJFINSV, TATASTEEL, NESTLEIND, BAJFINANCE, DRREDDY, KOTAKBANK, SHRIRAMFIN) against exchange corporate-action / ISIN master evidence. Do not interpret as constituent events by themselves.
3. Resolve TATAMOTORS/TMPV continuity with official corporate-action and symbol-history records.
4. Compare candidate windows with bhavcopy ISIN activity and available AMC portfolio snapshots as corroboration, not as replacements for official index notices.
5. Preserve any disagreement or unsupported event as unresolved; require independent human sign-off before verified membership status.

## Limitations

- The longest gaps are wide: e.g. 2021-09-03 to 2022-07-28 and 2023-05-22 to 2024-02-05. These diffs cannot identify exact effective dates.
- Wayback captures are supplementary archival evidence. Retrieval, schema validation and 50-row counts do not authenticate the contents as the official membership state on every intervening trading day.
- Snapshot pair differences are not the registered 34-transition ledger and do not verify any of those transitions.
- The mandatory 50-members-per-trading-day invariant has not been evaluated by this report.
- No membership interval, canonical membership data, model, holdout or trading permission was changed.
