# Weekly market-document refresh — 2026-11-08

## Run status

- Scope: exchange-wide NSE operational notices and issuer filings relevant to the registered NIFTY 50 pilot only.
- Result: **PARTIAL SOURCE DISCOVERY — NOT A COMPLETE VERIFIED REFRESH**.
- Repository branch: `main`.
- No model data, labels, historical prices, TRI, membership intervals, holdout data, model weights, or execution controls were changed.
- Research status remains `RESEARCH_HOLD`; final holdout remains locked.

## Verified primary-source observations

### Exchange calendar

- NSE's official 2026 market-holidays page lists the 2026 equity holidays and explicitly notes the 8 November 2026 Diwali Laxmi Pujan holiday with Muhurat Trading exception.
- Source: https://www.nseindia.com/resources/exchange-communication-holidays
- The repository already contains the 2026 special-session/calendar implementation and prior source archive. This run did not download or hash a new calendar circular PDF.

### Asian Paints (ASIANPAINT) — NIFTY 50 constituent

- NSE's official security quote page identifies Asian Paints as an Index: NIFTY 50 constituent.
- Source: https://www.nseindia.com/get-quote/equity/ASIANPAINT/Asian-Paints-Limited
- Asian Paints' official investor statutory-filings page reports that shareholders approved the appointment of Leo Puri as an Independent Director on 6 November 2026; he is to assume the Board Chair role from 23 January 2027 after the outgoing Chairman's term ends on 22 January 2027.
- Source: https://www.asianpaints.com/more/investors/investors-landing-page.html?q=statutory-filings
- The same issuer page reports the 29 October 2026 board outcome, including approval of an interim dividend of ₹5.75 per equity share for FY ending 31 March 2027, with payment on or after 13 November 2026.
- The NSE quote page displays the ₹5.75 interim dividend with ex-date and record date 4 November 2026.
- The official issuer page and NSE quote page were reviewed as web pages; the underlying announcement PDFs were not downloaded into this repository in this run. Therefore these are **page-level source observations**, not archived-byte/hash-verified evidence. No corporate-action ledger row or price adjustment was written.

## Repository integrity findings / blockers

1. `data/reference/nifty50_membership.csv` currently has only its header and no effective-dated constituent rows. Asian Paints' current NIFTY 50 status was independently visible on its NSE quote page, but the repository's historical membership ledger remains empty. The refresh must not use an empty/incomplete register to infer other issuer membership.
2. `data/reference/corporate_actions.csv` currently contains two legacy TMPV entries whose original PDFs are not archived; these do not establish a complete NIFTY 50 corporate-action ledger.
3. `data/reports/nifty50_notice_triage.json` records `coverage_complete: false` and a human-review queue of 95 rows. This is an existing historical archive/triage limitation, not a new failure from this run.
4. The existing source archive reports 7/7 weekend circular PDFs archived with independent review pending; the ad-hoc holiday archive reports 2/3 archived, with NSE/CMTR/57285 blocked by HTTP 403. These existing gaps remain unresolved.
5. BSE issuer-level primary filing PDFs and a complete NSE/BSE new-document delta were not archived and hashed in this first pass. Third-party announcement aggregators were treated only as discovery aids, not as authoritative evidence.

## Changes made

- Added this dated audit report only.
- No issuer event was added to `data/reference/corporate_actions.csv`, because original source PDFs and byte hashes were not acquired in this run.
- No calendar rows were changed.
- No model or trading configuration was changed.

## Required next implementation

Build a GitHub Actions weekly workflow and source-acquisition pipeline that:
- checks NSE and BSE circulars/notices and official issuer filings for all currently and historically eligible NIFTY 50 pilot constituents;
- captures original source bytes, source references, publication/effective dates, retrieval time (Asia/Kolkata), SHA-256, and supersession/cancellation relationships;
- maintains separate exchange-notice and issuer-corporate-action ledgers;
- extracts dividends, buybacks, splits, bonuses, rights, mergers/demergers, board meetings, results, and other material disclosures without silently changing historical prices/TRI;
- validates all changes, runs tests, and commits only source-backed records to `main`;
- fails closed on missing constituent membership, unavailable primary sources, ambiguous dates, or incomplete extraction; and
- reports every weekly run, including no-change and incomplete-source outcomes.

**Important:** This report is an initial bounded reconnaissance, not evidence that all NSE/BSE notices or all NIFTY 50 company filings have been checked.