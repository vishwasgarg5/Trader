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


## Follow-up: official archive corroboration (2026-11-07)

A subsequent independent check of the publisher's official press-release archive and fixed-income index materials found corroborating title/scope evidence for the three unresolved rows. This narrows the uncertainty about whether these notices concern NIFTY 50 equity membership, but it does **not** recover the original PDFs, establish their original byte hashes, or constitute human sign-off.

| Notice ID | Publisher archive corroboration | Scope evidence | Disposition |
|---|---|---|---|
| `NSE-ARCHIVE-2018-06-05-209df26d1951` | The official press-release archive lists 05 June 2018: “Change in NIFTY 10 Year SDL Index w.e.f. June 06, 2018”. [Archive](https://www.niftyindices.com/press-release) | The publisher's NIFTY 10 Year SDL Index description identifies the instrument as a portfolio of State Development Loans. [Index description](https://www.niftyindices.com/indices/fixed-income/sdl-indices/nifty-10-year-sdl-index) | `TITLE_AND_SCOPE_CORROBORATED_NOT_PRIMARY_PDF_AUTHENTICATED` |
| `NSE-ARCHIVE-2019-07-16-3a8719394912` | The official press-release archive lists 16 July 2019: “Change in NIFTY 10 Year SDL Index w.e.f. July 17, 2019”. [Archive](https://www.niftyindices.com/press-release) | The same publisher index description identifies NIFTY 10 Year SDL as a State Development Loan index. [Index description](https://www.niftyindices.com/indices/fixed-income/sdl-indices/nifty-10-year-sdl-index) | `TITLE_AND_SCOPE_CORROBORATED_NOT_PRIMARY_PDF_AUTHENTICATED` |
| `NSE-ARCHIVE-2023-03-14-5b13b76a2af9` | The official 2023 archive lists 14 March 2023: “NSE Indices launches Nifty SDL Jul 2028 Index”. [2023 archive](https://www.niftyindices.com/press-release?date=2023) | The publisher's fixed-income methodology describes the Nifty SDL Jul 2028 Index as a portfolio of State Development Loans; its portfolio material records a 15 March 2023 launch date. [Methodology](https://www.niftyindices.com/Methodology/Method_NIFTY_Fixed_Income_Indices.pdf) · [Portfolio](https://niftyindices.com/Portfolio/Nifty_SDLJul2028Index_Portfolio.pdf) | `TITLE_AND_SCOPE_CORROBORATED_NOT_PRIMARY_PDF_AUTHENTICATED` |

### Evidence limitations and required handling

- The archive listing and current index materials are publisher-origin corroboration, not substitutes for the three missing original press-release PDFs.
- No original PDF bytes were obtained in this follow-up; no source-document path or SHA-256 hash is claimed.
- The three records may be proposed for human-confirmed out-of-scope disposition for the NIFTY 50 equity pilot, but their review states must remain unchanged until an independent reviewer records the decision.
- Keep all three retrieval exceptions visible in reconciliation and coverage reporting until the missing originals are recovered or an independent reviewer documents an approved archival substitute under the protocol.
- This follow-up does not close annual archive completeness, transition reconciliation, or point-in-time membership verification.

