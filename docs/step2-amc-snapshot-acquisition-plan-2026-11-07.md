# Step 2 revised historical snapshot acquisition plan

Date: 2026-11-07  
Branch: `main`  
Prior audit commit: `cce69127454e51af7f048ac939db7d71607bde66`

## Decision

The previous audit's assumption that progress depended on an NSE public archive of dated full constituent lists is withdrawn. The snapshot acquisition plan now uses monthly portfolio disclosures from Nifty 50 ETFs and index funds as independent, dated reconstruction checks, with NSE/Nifty Indices notices and exchange circulars remaining the primary authority for membership events.

Do not wait for a new NSE archive publication.

## Regulatory basis and source routes

SEBI's mutual fund disclosure rules require monthly scheme portfolio disclosure, including ISIN, as of month-end, on the AMC website in a downloadable format. The SEBI master circular and disclosure material are the regulatory basis:
- SEBI circular / disclosure text: https://www.sebi.gov.in/cms/sebi_data/attachdocs/1347547815927.pdf
- SEBI consolidated circular (2025): https://www.sebi.gov.in/web/?file=https%3A%2F%2Fwww.sebi.gov.in%2Fsebi_data%2Fmutualfundfile%2Fjun-2025%2F1750328355935.pdf
- SEBI master circular (2024 copy): https://fimmda.org/LinkFiles/VIII_SEBI_MCMF.pdf

Useful AMC archive routes identified:
1. SBI Mutual Fund portfolio archive: https://www.sbimf.com/portfolios  
   The official page exposes Monthly / Fortnightly / Half Yearly frequency and year choices from 2013 onward, including 2018–2024. Scheme and month must be selected to retrieve the source file. The page is a source route; this audit has not yet downloaded any dated file.
2. HDFC Mutual Fund monthly portfolio disclosure: https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio  
   Official current page lists Nifty 50 Index Fund and NIFTY 50 ETF monthly disclosure files. The publicly indexed current page does not establish availability of its 2018–2024 files; historical archive access remains to be tested.
3. Independent index of AMC disclosure files and Internet Archive copies: https://amcs.fund/month  
   Its methodology states that it ingests AMC source files and links the source files and archived copies. Use this as a discovery/secondary index only; verify each file against the original AMC disclosure URL and preserve the original source bytes.

SEBI's passive-fund disclosure provisions also require disclosure of the names/exposure of top seven issuers/stocks monthly and constituent changes on the day of change. This top-seven requirement is not a substitute for the complete monthly scheme portfolio disclosure.

## Snapshot interpretation rules

A monthly index-fund/ETF portfolio is an independent reconstruction check, not a primary index-membership declaration. Do not assume that every fund's equity rows are exactly the 50 benchmark constituents. Preserve and classify:
- cash, TREPS, receivables, margin and other non-equity rows;
- futures or other derivative exposure;
- temporary corporate-action entitlements and dummy securities;
- fund sampling/tracking differences and any non-index holdings;
- securities whose ISIN/name changes require identity mapping.

For each candidate fund-month:
1. Save the original AMC disclosure bytes and original URL; do not rely only on a third-party mirror.
2. Record the portfolio's stated as-of date, publication/retrieval date, AMC, scheme, scheme benchmark and scheme identity.
3. Hash original bytes with SHA-256.
4. Parse all equity/ equity-related rows, preserving issuer name, symbol where present, ISIN, quantity, market value and % NAV.
5. Map instruments to issuer/security identity through a separately versioned identity map.
6. Compare the equity constituent set with the Nifty 50 transition replay and other funds' sets.
7. Flag differences; never trim/add names just to force 50.
8. Where multiple funds disagree, preserve all variants and investigate tracking, corporate action, data or scheme-specific explanations.

Prefer two or more independent AMCs for each annual anchor where available. Record whether each AMC source is primary (original AMC-hosted file) or secondary (mirror/archive).

## Anchor and interval design

Acquire at least one month-end full-portfolio anchor for each calendar year 2018–2024 (prefer December month-end where the fund existed and its disclosure is retrievable). The seven year-end anchors satisfy annual coverage sampling, but are not sufficient alone to prove every transition.

Also acquire monthly portfolio snapshots immediately before and after each material Nifty 50 transition, or the closest available month-end disclosures, and additional dates around any unexplained discrepancy. Where month-end cadence is too coarse to resolve a transition, rely on the primary NSE/Nifty Indices notice/circular chain and seek an additional contemporaneous source.

For each annual anchor:
- Replay primary-source NSE/Nifty Indices membership events forward/backward from an authenticated anchor, using effective dates rather than announcement dates.
- Compare the reconstructed set to each AMC snapshot after applying explicit portfolio-vs-index normalization rules.
- Require set equality only where the portfolio source is demonstrated to represent the full benchmark constituent universe. Otherwise report the precise symmetric difference and classify the discrepancy; do not claim a match.
- A 50-name count is necessary for ordinary Nifty 50 dates but not sufficient. Compare exact issuer/security identities.
- Preserve the JIOFIN temporary inclusion episode as an explicit special-event phase; do not force the ordinary 50-name rule onto the documented temporary 51-member treatment.

A year-end match does not rule out two offsetting missing/misdated events between anchors. Thus every transition remains subject to primary notice verification and transition-adjacent snapshot checks.

## Seven-year acquisition register

Create one row per AMC/scheme/as-of month with:
- calendar_year, as_of_date, AMC, scheme_name, scheme_identifier;
- benchmark_name and benchmark_identifier;
- source_url, source_type (AMC_PRIMARY / ARCHIVE_MIRROR / OTHER);
- retrieved_at, original_filename, sha256, archived_path;
- parsed_equity_rows, distinct_issuer_count, distinct_ISIN_count;
- non_equity_rows, derivative_rows, corporate_action_rows;
- candidate_constituent_set_path, comparison_status, discrepancy_reason;
- reviewer, reviewed_at, human_review_status.

Target anchor months:
- 2018-12 (or nearest month-end available)
- 2019-12
- 2020-12
- 2021-12
- 2022-12
- 2023-12
- 2024-12

For each year, seek at least two AMC sources where feasible. Record missing source availability transparently; do not infer that an unavailable month did not exist.

## Step 2 status

This plan changes the source strategy, not the evidence status. No historical AMC portfolio file has yet been downloaded and hashed as part of this audit. No anchor set has been validated, no transition has been promoted from SAMPLE_ONLY, and no point-in-time membership intervals have been generated.

Step 2 remains **OPEN / NOT COMPLETE**. Independent human review remains a mandatory acceptance gate; AI-assisted triage and source discovery are not human sign-off. Research hold and the prohibition on paper/live trading remain unchanged.
