# NIFTY 50 dated-snapshot reconciliation — 2023 (initial pass)

**Status:** PARTIAL / EVIDENCE_ONLY. No membership intervals were generated or promoted.

## Scope of this pass

This pass tests the July 2023 constituent-change sequence against an independently published monthly constituent table. It does not claim a full daily or month-end snapshot series.

## External snapshot located

- Publisher: Securities and Exchange Board of India (SEBI), *Annexure — Current Statistics*, August 2023.
- Table 25: “Component Stocks: Nifty 50 Index during July, 2023”.
- PDF: https://www.sebi.gov.in/sebi_data/commondocs/aug-2023/Annexure_Current_statistics_Aug_2023_p.pdf
- The table states its source is NSE and lists 50 securities.
- It includes LTIMindtree Ltd. (row 30) and does not list HDFC Ltd. The table therefore provides a useful monthly cross-check of the 4 July 2023 HDFC-out / LTIM-in announcement, effective 13 July 2023.
- It is a monthly “during July” table, not a point-in-time daily snapshot explicitly dated 13 July. It cannot independently establish the exact effective-close membership transition.
- The table does not name JIOFIN or the pre-listing demerger placeholder. Because the temporary placeholder may have a distinct index identity/price treatment, this table cannot validate or falsify the 20 July dummy inclusion event. Do not infer its absence from a missing listed-security name.
- The monthly table alone does not resolve the placeholder-to-listed identity treatment on 21 August or the JIOFIN removal on 7 September.

## Repository state discovered

- `data/reference/nifty50_membership.csv` currently contains only its header; there are no membership intervals to compare.
- The 2023 row in `data/reference/nifty50_annual_coverage.csv` remains `NOT_STARTED` with `snapshot_reconciliation_complete` blank and `official_notice_search_complete=false`.
- The 2023 special-event register contains the three JIOFIN dummy/listed/removal events, all `AI_REVIEWED_PENDING_HUMAN_SIGNOFF`; they are not independently approved membership intervals.
- The July 2023 HDFC/LTIM transition rows remain `SAMPLE_ONLY`.

## Reconciliation decisions

1. Record the SEBI July table as an external monthly corroboration lead, not as a daily point-in-time membership source.
2. The HDFC/LTIM event is directionally consistent with the monthly table: LTIM is listed; HDFC Ltd. is not.
3. Do not mark the JIOFIN dummy event reconciled from this table. The placeholder is not identified in the component-name list.
4. Do not backfill `nifty50_membership.csv` from this single monthly table.
5. Obtain the official NSE Indices July, August and September 2023 monthly Market Capitalisation/Weightage reports (and preferably daily constituent archives around 13 July, 20 July, 21 August and 7 September). Preserve original bytes, source URL, retrieval timestamp and SHA-256 before parsing.
6. Compare exact 50/51 constituent counts, placeholder identifiers, names/symbol aliases, and close-date conventions against the notice sequence. Resolve differences with the NSE primary notices and circulars.
7. Require independent human sign-off before any interval promotion.

## Next checks

- Acquire July/August/September 2023 NSE monthly constituent reports from the official historical reports archive.
- Inspect the source's reporting cut-off and whether the report represents month-end holdings or a within-month list.
- Reconcile the exact July 13 and July 20 state transitions separately; do not conflate the HDFC/LTIM rebalance with the demerger placeholder.
- Repeat for the August 21 identity transition and September 7 removal, then extend the same method across 2018–2024.

**Gate:** closed. This report is research evidence only and does not authorize production use or live trading.
