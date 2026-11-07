# Step 2 source-retrieval audit

Audit date: 2026-11-07  
Base: `main` at `e816c5a5381156e202b5950497f0b4f497ff246a`

## Purpose

Record retrieval outcomes for three archive entries that the annual notice inventory currently flags as missing local PDFs. This is an evidence-log update only. It does not authorize a membership decision, independent sign-off, or a change to any verification status.

## Retrieval results

| Notice ID | Official archive URL | Inventory classification | Retrieval result in this audit | Evidence disposition |
|---|---|---|---|---|
| `NSE-ARCHIVE-2018-06-05-209df26d1951` | https://www.niftyindices.com/Press_Release/ind_prs05062018.pdf | Fixed-income NIFTY 10 Year SDL notice; not a flagship NIFTY 50 equity event, per archive title | Direct source open was inaccessible in the web retrieval channel | PDF not obtained; no local hash; retain as unresolved source retrieval |
| `NSE-ARCHIVE-2019-07-16-3a8719394912` | https://www.niftyindices.com/Press_Release/ind_prs16072019_1.pdf | Fixed-income NIFTY 10 Year SDL notice; not a flagship NIFTY 50 equity event, per archive title | Direct source open was inaccessible in the web retrieval channel | PDF not obtained; no local hash; retain as unresolved source retrieval |
| `NSE-ARCHIVE-2023-03-14-5b13b76a2af9` | https://www.niftyindices.com/Press_Release/ind_prs14032023.pdf | Nifty SDL Jul 2028 fixed-income index launch, per archive title | Official URL returned the publisher's 404 page | PDF not obtained; no local hash; retain as unresolved source retrieval |

## Required next actions

1. Retry retrieval through the NSE Indices press-release archive and an authorized historical archive/vendor source. Preserve the original response bytes and URL.
2. If a PDF is obtained, verify the PDF signature, compute SHA-256, store it under `data/reference/source_documents/`, and update the inventory path/hash using the repository's existing schema.
3. If the original is permanently unavailable, record the independent archive evidence used to establish its title and scope; do not silently treat the missing PDF as a verified exclusion.
4. Obtain independent human review for all scope exclusions and candidate transitions.
5. Reconcile the generated triage report with the current inventory and queue before declaring the evidence package internally consistent.

## Current Step 2 disposition

**OPEN — NOT READY.** The latest triage report in the base commit records 684 inventory rows and 95 review-queue rows, while the current review queue contains 108 rows. The report must be regenerated from the exact current source files. Annual coverage, supersession review, snapshot reconciliation, transition sign-off, and point-in-time membership generation remain blocked.

No membership intervals are generated or modified by this audit.
