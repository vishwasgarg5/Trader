# NSE archive catalog / annual inventory reconciliation

Review date: 2026-11-07  
Repository: `vishwasgarg5/Trader`  
Branch: `main`

## Result

A URL-keyed comparison of the checked-in discovery catalog and annual notice inventory was performed.

| Dataset | Rows | Meaning |
|---|---:|---|
| `nifty50_archive_discovery_catalog.csv` | 697 | All discovered archive entries, including title-screened non-candidates |
| `nifty50_annual_notice_inventory.csv` | 687 | Review-candidate inventory plus separately registered event sources |
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
| 2024-12-02 | Corporate Adjustment for Strides Pharma Science Ltd. | **Blocked**: the same-date local extraction is the Nifty IPO replacement notice, not the Strides corporate-adjustment release; correct source bytes and hash required |

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

This reconciliation explains the 15 catalog-only and two inventory-only URL differences. It does **not** complete annual archive discovery or source screening. The 2020 CPSE revision and the two 2024 Index Maintenance Sub-Committee meeting notices remain explicit triage work. The Strides corporate-adjustment source remains blocked because the local same-date extraction is the separate Nifty IPO notice; the correct PDF bytes and matching hash must be archived before scope can be accepted. The three missing-PDF retrievals remain unresolved. The seven annual coverage rows must stay `NOT_STARTED`, and all `official_notice_search_complete` flags must stay false until full archive/ad-hoc reconciliation, supersession review, snapshot reconciliation, and independent review are evidenced.

No constituent intervals were created or modified. No row was marked `VERIFIED`. Research hold and live-execution-disabled controls remain unchanged.



## Source-identity mismatch — 2024-12-02 Strides corporate adjustment

The official [2 December 2024 Strides corporate-adjustment URL](https://www.niftyindices.com/Press_Release/ind_prs02122024_1.pdf) is distinct from the same-date Nifty IPO replacement URL. The checked-in extracted text at `NSE-ARCHIVE-2024-12-02-295b1f169428.txt` is explicitly the **Nifty IPO** replacement notice, not the Strides notice. The Git tree also shows the two same-date PDF paths have identical blob content, so the local Strides-labelled artifact is not independent evidence for the Strides URL. The catalog row is therefore marked `SOURCE_ARCHIVE_IDENTITY_MISMATCH_BLOCKED`; it is not screened out of Nifty 50 scope. Correct source bytes, source URL/path reconciliation, SHA-256 verification, and independent review are required. A regression test prevents the Nifty IPO extraction from being reused as Strides evidence. No membership or annual coverage status was advanced.

## Latest fail-closed readiness snapshot

The latest completed protocol workflow audit (run [#42381606001](https://github.com/vishwasgarg5/Trader/actions/runs/42381606001), commit `58d442ee`) reported:

| Gate | Observed | Required for Step 2 |
|---|---:|---|
| Effective-dated membership intervals | 0 rows / 0 verified | Complete source-backed interval history |
| Transition register | 34 rows / 0 verified | Every in-scope transition verified and independently signed off |
| Annual coverage | 0 of 7 years complete | 2018–2024 each complete |
| Special membership events | 3 rows / 0 verified | All special events independently reviewed |
| Annual notice inventory | 687 unresolved rows | Scope and disposition reviewed with independent human sign-off |
| Archive discovery catalog | 697 unresolved rows (694 unreviewed; 3 pending sign-off or blocked) | Candidate and non-candidate dispositions reviewed with independent human sign-off |

The archive reconciliation sub-audit matched 112 of 117 curated notice-register rows to inventory records, with 5 register-only rows; it found 15 catalog-only URLs and 2 inventory URLs absent from the catalog. Across the inventory and register evidence checks, 798 local source files had matching recorded hashes and 6 rows had no local source path/hash recorded. These are structural audit counts, not proof that the contents were interpreted correctly or that the full archive search is complete.

The counts above distinguish raw `UNREVIEWED` catalog rows from all unresolved rows. AI scope exclusions still awaiting human sign-off and source-identity mismatches remain unresolved; `SCREENED_NO_NIFTY50_CHANGE` inventory rows are AI screens, not completed independent reviews. The audit explicitly returned `point_in_time_membership_verified=false` and `ready_for_pit_research=false`. The pilot must remain blocked until primary-source review, supersession reconciliation, 50-member snapshot checks (including documented special-event exceptions), and independent reviewer sign-off are complete.
