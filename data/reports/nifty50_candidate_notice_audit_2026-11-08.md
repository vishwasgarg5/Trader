# NIFTY 50 candidate notice audit — 2026-11-08

## Purpose and boundary

This is an inventory-based second-pass audit aid for the NIFTY 50 pilot. It records the 20 rows currently marked `CANDIDATE` in `data/reference/nifty50_annual_notice_inventory.csv`, together with the repository's existing event summaries, source-document paths, and SHA-256 digests.

It is **not** independent human verification, does not promote any candidate to verified status, and does not create membership intervals. The source inventory, review queue, transition register, and model inputs are unchanged. All 20 entries remain pending independent human sign-off. The 2023 JIOFIN episode must remain a special temporary-membership sequence rather than being forced into a 50-member assumption.

## Candidate ledger

| Notice | Announcement | Effective date in inventory | Candidate interpretation |
|---|---:|---:|---|
| N50-NOTICE-2018-02-21 | 2018-02-21 | 2018-04-02 | OUT AMBUJACEM, AUROPHARMA, BOSCHLTD; IN BAJAJFINSV, GRASIM, TITAN |
| N50-NOTICE-2018-08-28 | 2018-08-28 | 2018-09-28 | OUT LUPIN; IN JSWSTEEL |
| N50-NOTICE-2019-02-25 | 2019-02-25 | 2019-03-29 | OUT HINDPETRO; IN BRITANNIA |
| N50-NOTICE-2019-08-28 | 2019-08-28 | 2019-09-27 | OUT IBULHSGFIN; IN NESTLEIND |
| N50-NOTICE-2020-02-18 | 2020-02-18 | 2020-03-27 (superseded) | Original YESBANK/SHREECEM review proposal; do not apply this date |
| N50-NOTICE-2020-03-16 | 2020-03-16 | 2020-03-19 | Accelerates YESBANK removal and SHREECEM inclusion |
| N50-NOTICE-2020-03-23 | 2020-03-23 | 2020-03-27 | Deferment evidence; does not reverse the already effective 2020-03-19 NIFTY 50 change |
| N50-NOTICE-2020-03-25 | 2020-03-25 | 2020-03-27 | Further deferment evidence; no new NIFTY 50 constituent change established |
| N50-NOTICE-2020-05-13 | 2020-05-13 | 2020-06-26 (notice-wide date) | Confirms NIFTY 50 and NIFTY Bank had already rebalanced on 2020-03-19; does not reverse that event |
| N50-NOTICE-2020-07-02 | 2020-07-02 | 2020-07-31 | OUT VEDL; IN HDFCLIFE |
| N50-NOTICE-2020-08-20 | 2020-08-20 | 2020-09-25 | Candidate OUT INFRATEL, ZEEL; IN DIVISLAB, SBILIFE; verify precise scope against the primary PDF |
| N50-NOTICE-2021-02-23 | 2021-02-23 | 2021-03-31 | OUT GAIL; IN TATACONSUM |
| N50-NOTICE-2022-02-24 | 2022-02-24 | 2022-03-31 | OUT IOC; IN APOLLOHOSP |
| N50-NOTICE-2022-09-01 | 2022-09-01 | 2022-09-30 | OUT SHREECEM; IN ADANIENT |
| N50-NOTICE-2023-07-04 | 2023-07-04 | 2023-07-13 | OUT HDFC; IN LTIM |
| N50-NOTICE-2023-07-17 | 2023-07-17 | 2023-07-20 | Temporary JIOFIN spin-off/dummy episode; 51 securities |
| N50-NOTICE-2023-08-18 | 2023-08-18 | 2023-08-21 | JIOFIN listing and dummy replacement; 51 securities |
| N50-NOTICE-2023-09-05 | 2023-09-05 | 2023-09-07 | JIOFIN removed; constituent count returns to 50 |
| N50-NOTICE-2024-02-28 | 2024-02-28 | 2024-03-28 | OUT UPL; IN SHRIRAMFIN |
| N50-NOTICE-2024-08-23 | 2024-08-23 | 2024-09-30 | OUT DIVISLAB, LTIM; IN BEL, TRENT |

## Required verification before interval construction

1. Independently inspect each archived official PDF and verify its SHA-256 against the inventory.
2. Confirm that each notice explicitly concerns flagship NIFTY 50 (not NIFTY Next 50, NIFTY50 Equal Weight alone, or a strategy/sector index).
3. Verify effective dates against official notices and the trading calendar; store the final trading session before each effective date separately.
4. Resolve the 2020 supersession/deferment chain as one event with the operative 2020-03-19 date.
5. Resolve the 2023 JIOFIN dummy-to-listed identity chain and temporary 51-security count without forcing an ordinary 50-name interval.
6. Cross-check each transition against a second independent official source where available.
7. Only after independent human approval, write verified OUT/IN symbols and effective dates into the canonical transition ledger; then derive membership intervals and reconcile to dated constituent snapshots.

## Snapshot of the audit boundary

- Candidate rows in inventory: 20.
- Candidate source-document paths are recorded in the inventory; presence and digest must be rechecked during reviewer sign-off.
- Verified membership intervals produced by this audit: 0.
- Changes made to canonical membership data: none.
- Holdout access: none.
- Paper/live trading authorization: none.
- Pilot gate: RESEARCH HOLD.

This report is a review aid only. A candidate notice, a plausible transition, a source hash, or a successful CI run is not a verified point-in-time membership interval.
