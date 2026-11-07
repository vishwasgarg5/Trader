# NSE May 2019 source recheck

Started: 2026-11-07
Branch: main

## Scope
Recheck the already archived official NSE Indices PDFs for:
- 2019-05-21: data/reference/source_documents/NOTICE-NSE-ARCHIVE-2019-05-21-a094c82572dc.pdf
- 2019-05-28: data/reference/source_documents/NOTICE-NSE-ARCHIVE-2019-05-28-35a01966649a.pdf

## Required automated verification
The next NSE evidence-refresh workflow must:
1. Recompute SHA-256 from each archived PDF's actual bytes and compare with the annual inventory.
2. Validate PDF signatures and parse every page.
3. Preserve extracted text and report page counts, extraction status, and hash mismatches.
4. Keep both inventory rows unchanged unless complete-document review supports a scope decision.
5. Never infer NIFTY 50 exclusion from a title alone and never create membership intervals or human sign-off.

## Current disposition
Both archive paths were confirmed present on main. This note does not claim that either PDF's hash has been independently recomputed or that either document has passed full-text scope review. The existing 2019-05-21 audit disposition remains DISCOVERED_UNREVIEWED pending the evidence-refresh artifact and page-level inspection. The 2019-05-28 item also remains unclassified pending the same checks.

## Safety
Research remains HOLD. Annual coverage remains NOT_STARTED. No PIT membership rows, model promotion, final-holdout evaluation, or live execution are authorized by this source recheck.
