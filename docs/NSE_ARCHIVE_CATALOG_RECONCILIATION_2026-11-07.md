# NSE archive catalog / annual inventory reconciliation

Review date: 2026-11-07  
Repository: `vishwasgarg5/Trader`  
Branch: `main`

## Result

A URL-keyed comparison of the checked-in discovery catalog and annual notice inventory was performed.

| Dataset | Rows | Meaning |
|---|---:|---|
| `nifty50_archive_discovery_catalog.csv` | 697 | All discovered archive entries, including title-screened non-candidates |
| `nifty50_annual_notice_inventory.csv` | 684 | Review-candidate inventory plus separately registered event sources |
| Catalog-only URLs | 15 | Archive entries not copied into the candidate inventory |
| Inventory-only URLs | 2 | Special-event sources hosted on the NSE archives host, not discovered as press-release archive entries |

The 15 catalog-only URLs are all explicitly `review_candidate=false`. Their exclusion from the annual candidate inventory is therefore consistent with the discovery pipeline's two-tier design; it is not evidence that their source contents were screened. The 15 rows remain `UNREVIEWED` in the catalog. No scope status, membership event, or annual coverage flag was changed.

## Catalog-only records

| Publication date | Archive title | Triage note |
|---|---|---|
| 2018-03-09 | Discontinuation of NIFTY_AAA_Index Series | Outside the research start date (2018-04-01); retain catalog provenance |
| 2018-04-17 | IISL Launches NIFTY200 Quality 30 Index | Launch title; not a constituent-change title |
| 2018-04-24 | IISL Launches NIFTY Equity Savings Index | Launch title; not a constituent-change title |
| 2018-06-16 | Minutes of Order 14.06.2018 - IISL-SGX Arbitration | Legal/administrative title; not a constituent-change title |
| 2018-12-03 | NSE India ETF Conference 2018 | Event announcement title |
| 2020-01-17 | Revision in NIFTY CPSE Index | **Needs scope triage**; title says revision but the current candidate keyword rule did not include this wording |
| 2021-11-09 | UTI International launches UTI India Sovereign Bond ETF | Product launch title |
| 2022-03-21 | Joint Press Release on Introduction of Common Industry Classification Structure for Companies Listed and Traded at NSE and BSE | Market-wide classification announcement; keep as a source-review candidate if linked to index methodology |
| 2022-12-20 | Revision in Nifty G-Sec Sep 2032 V1 Index | Fixed-income index title; outside flagship equity universe by title |
| 2023-10-27 | Proposed revision in Nifty India Select 7 Government Bond Index | Government-bond index title; outside flagship equity universe by title |
| 2024-02-15 | Higher frequency for real time index dissemination | Dissemination announcement |
| 2024-02-27 | Meeting of the Index Maintenance Sub-Committee (Equity) | **Retain for scope review**; meeting notice alone does not establish an index decision |
| 2024-08-16 | Meeting of the Index Maintenance Sub-Committee (Equity) | **Retain for scope review**; meeting notice alone does not establish an index decision |
| 2024-11-28 | Corporate Adjustment for Emkay Taps and Cutting Tools Ltd. in Nifty SME Emerge | Corporate-action title for SME Emerge, not flagship Nifty 50 by title |
| 2024-12-02 | Corporate Adjustment for Strides Pharma Science Ltd. | Archived source text scopes the dummy inclusion to Nifty Microcap 250 and Nifty Total Market; AI screen excludes flagship Nifty 50 membership, pending human sign-off |

## Inventory-only sources

These two rows are not archive-catalog mismatches: they are separately sourced special-membership evidence and are intentionally represented in the event ledger.

- 2023-07-17, temporary member episode: `https://nsearchives.nseindia.com/web/sites/default/files/2023-08/PR_cc_17072023.pdf`
- 2023-08-18, listing and dummy replacement: `https://nsearchives.nseindia.com/web/sites/default/files/2023-08/PR_list_18082023.pdf`

## Retrieval failures remain open

The annual inventory still has three source URLs whose retrieval did not produce verified PDF bytes:

- 2018-06-05: `https://www.niftyindices.com/Press_Release/ind_prs05062018.pdf`
- 2019-07-16: `https://www.niftyindices.com/Press_Release/ind_prs16072019.pdf`
- 2023-03-14: `https://www.niftyindices.com/Press_Release/ind_prs14032023.pdf`

The official archive page independently displays the 2019-07-16 title as “Change in NIFTY 10 Year SDL Index w.e.f. July 17, 2019”; this confirms the archive listing/title, not the missing PDF bytes or contents. Source: https://www.niftyindices.com/press-release

## Acceptance impact

This reconciliation explains the 15 catalog-only and two inventory-only URL differences. It does **not** complete annual archive discovery or source screening. The 2020 CPSE revision and the two 2024 Index Maintenance Sub-Committee meeting notices remain explicit triage work. The Strides corporate-adjustment notice is now AI-screened as outside flagship Nifty 50 scope, with human sign-off still pending. The three missing-PDF retrievals remain unresolved. The seven annual coverage rows must stay `NOT_STARTED`, and all `official_notice_search_complete` flags must stay false until full archive/ad-hoc reconciliation, supersession review, snapshot reconciliation, and independent review are evidenced.

No constituent intervals were created or modified. No row was marked `VERIFIED`. Research hold and live-execution-disabled controls remain unchanged.


## Additional source triage — 2024-12-02 Strides corporate adjustment

The archived extracted text for the official [2 December 2024 Strides Pharma Science corporate-adjustment release](https://www.niftyindices.com/Press_Release/ind_prs02122024_1.pdf) identifies the dummy-symbol inclusion in **Nifty Microcap 250** and **Nifty Total Market** only. Its operative section contains no flagship Nifty 50 membership action. The discovery-catalog row remains `review_candidate=false` and is now marked `AI_SCOPE_EXCLUSION_PENDING_HUMAN_SIGNOFF`; this is an automated scope triage, not independent approval or annual-coverage completion. A regression test locks the source-text scope and status. No membership interval or transition row was created or changed.
