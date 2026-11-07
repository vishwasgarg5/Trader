# Step 2 revised historical snapshot acquisition plan

Date: 2026-11-07  
Branch: `main`  
Prior audit commit: `cce69127454e51af7f048ac939db7d71607bde66`

## Decision

The previous audit's assumption that progress depended on an NSE public archive of dated full constituent lists is withdrawn. The snapshot acquisition plan uses monthly portfolio disclosures from Nifty 50 ETFs and index funds as independent, dated reconstruction checks, with NSE/Nifty Indices notices and exchange circulars remaining the primary authority for membership events.

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

## Snapshot interpretation and immutable acquisition rules

A monthly index-fund/ETF portfolio is an independent reconstruction check, not a primary index-membership declaration. Do not assume that every fund's equity rows are exactly the 50 benchmark constituents. Preserve and classify:
- cash, TREPS, receivables, margin and other non-equity rows;
- futures or other derivative exposure;
- temporary corporate-action entitlements and dummy securities;
- fund sampling/tracking differences and any non-index holdings;
- securities whose ISIN/name changes require identity mapping.

For each candidate fund-month:
1. Retrieve the original AMC disclosure and save its original bytes unchanged before parsing. Record the original URL and retrieval timestamp. A mirror or Wayback copy must be labelled as such and must not be represented as an AMC-origin download.
2. Record three distinct dates: (a) portfolio `as_of_date` stated inside the disclosure, (b) `publication_date` stated by the AMC or evidenced by its page/metadata, and (c) `retrieved_at` timestamp for this acquisition. If a Wayback copy is used, additionally record `wayback_capture_timestamp`; never substitute its capture date for the portfolio as-of date. If publication date cannot be established, leave it null and record why.
3. Calculate SHA-256 over the exact original bytes and record the digest before parsing. Store raw bytes in an immutable, content-addressed archive path. Parser outputs, normalized rows and candidate sets belong in separate derived-artifact paths; never overwrite the raw file.
4. Parse all equity rows and preserve issuer name, symbol where present, ISIN, quantity, market value and % NAV. Preserve non-equity and derivative rows separately with row classifications.
5. Use ISIN as the primary instrument/security key. Names and symbols are descriptive attributes/aliases, not identity keys. Resolve corporate actions, renamed securities, mergers/demergers and symbol changes through a separately versioned identity/alias map; retain the original reported ISIN and name on every parsed row. Do not merge two different ISINs merely because their names look similar.
6. Compare the equity ISIN set with the point-in-time transition replay and other eligible funds' sets. Apply only pre-registered normalization rules; do not tune exclusions after observing a mismatch.
7. Flag every difference. Never trim/add names to force a 50-name count. Preserve the raw observed set and the normalized comparison set separately.
8. Record fund tracking, sampling, corporate-action and scheme-specific explanations for residual differences, with evidence references and reviewer status.

## Pre-registered fund consensus and confidence rule

The fund-count rule is fixed before historical holdings are inspected:
- **Three or more eligible funds:** require agreement among at least three funds on the normalized equity ISIN set for a full-confidence snapshot consensus. Identify each AMC, scheme and source file. A majority vote does not erase a dissenting fund; preserve and explain every dissent.
- **Exactly two eligible funds:** label the snapshot `REDUCED_CONFIDENCE`. It cannot qualify as a full-confidence consensus by itself. Require one additional, independently sourced corroborating item tied to the same as-of date or event window (for example, a verified official index constituent/factsheet artifact containing the complete universe, a contemporaneous primary index-maintenance record plus independently archived holdings evidence, or another genuinely independent full-portfolio source). Document why it is independent and what it corroborates.
- **Exactly one eligible fund:** it is not usable as a membership anchor or consensus observation. Retain it as a lead/supporting observation only.
- **Zero eligible funds:** record `NO_SOURCE`; do not infer membership.

An eligible fund must have a demonstrated Nifty 50 benchmark, a full portfolio disclosure (not top-seven-only), a usable stated as-of date, retrievable original bytes or a clearly labelled fallback copy, and parseable ISIN-level equity rows. A fund with sampling or unexplained non-index positions is not silently eligible for exact-universe consensus.

## Anchor and transition-bracketing design

Acquire at least one month-end full-portfolio anchor for each calendar year 2018–2024 (prefer December month-end where the fund existed and its disclosure is retrievable). The seven year-end anchors are backstops, not substitutes for transition coverage.

For each of the 34 registered transitions:
1. Acquire the closest available full-portfolio month-end snapshot strictly before the transition's effective date and the closest available full-portfolio month-end snapshot on or after the effective date. Link each deduplicated snapshot record to every transition it brackets.
2. Deduplicate the physical acquisition by `AMC + scheme_identifier + as_of_date`; do not duplicate raw bytes when one snapshot brackets multiple transitions. Keep a many-to-many snapshot/transition link table so event-level coverage remains explicit.
3. Derive the expected transition difference set from the final, supersession-checked primary notice chain before comparing holdings. Store exact expected additions and removals by ISIN, after resolving the notice's issuer/security identity through the versioned identity map. For a multi-name event, include every named addition/removal. Treat special phases such as the JIOFIN temporary 51-member episode as explicit dated set changes, not as a count tolerance.
4. Compare the observed normalized equity ISIN set difference between the before and after observations with the notice-derived expected set. For a fund/source demonstrated to represent the full benchmark, require exact set equality. Any unexplained extra/missing ISIN is a discrepancy; there is no generic allowance for a one-name difference. If month-end timing, implementation lag, fund tracking or corporate action could explain a difference, record the exact residual and corroborating evidence; do not relabel it as a pass.
5. Interpret timing only from `as_of_date`. Publication date, retrieval date and Wayback capture timestamp are provenance fields and must never drive before/after classification.
6. If month-end cadence cannot resolve the event or the observed difference does not match the expected set, seek closer contemporaneous evidence and retain the transition as unresolved until reconciled. The primary notice's effective date remains authoritative; an ETF's rebalance date does not replace it.

For each annual anchor:
- Replay primary-source NSE/Nifty Indices membership events forward/backward from an authenticated anchor, using effective dates rather than announcement dates.
- Compare the reconstructed set to each AMC snapshot after applying only the pre-registered portfolio-vs-index normalization rules.
- Require set equality only where the portfolio source is demonstrated to represent the full benchmark constituent universe. Otherwise report the precise symmetric difference and classify the discrepancy; do not claim a match.
- A 50-name count is necessary for ordinary Nifty 50 dates but not sufficient. Compare exact issuer/security identities by ISIN.
- Preserve the JIOFIN temporary inclusion episode as an explicit special-event phase; do not force the ordinary 50-name rule onto the documented temporary 51-member treatment.

A year-end match does not rule out two offsetting missing/misdated events between anchors. Every transition therefore remains subject to primary notice verification and transition-adjacent snapshot checks.

## Acquisition and reconciliation registers

Create one row per deduplicated AMC/scheme/as-of-date raw snapshot with:
- snapshot_id, AMC, scheme_name, scheme_identifier;
- benchmark_name and benchmark_identifier;
- as_of_date, publication_date, publication_date_source, retrieved_at;
- wayback_capture_timestamp (nullable);
- source_url, source_type (`AMC_PRIMARY` / `ARCHIVE_MIRROR` / `WAYBACK_CAPTURE` / `OTHER`);
- original_filename, sha256, raw_archived_path, raw_byte_count;
- parser_version, derived_output_path;
- parsed_equity_rows, distinct_issuer_count, distinct_ISIN_count;
- non_equity_rows, derivative_rows, corporate_action_rows;
- eligibility_status, consensus_status, discrepancy_reason;
- reviewer, reviewed_at, human_review_status.

Maintain a separate many-to-many transition coverage/reconciliation register with:
- snapshot_id, transition_id, bracket_role (`BEFORE` / `AFTER` / `SUPPORTING`);
- transition_effective_date, notice_chain_reference;
- expected_addition_ISINs, expected_removal_ISINs;
- observed_added_ISINs, observed_removed_ISINs;
- exact_match, residual_ISINs, residual_explanation, corroborating_source_ids;
- fund_count, confidence_status, reviewer, reviewed_at, human_review_status.

Target annual anchor months:
- 2018-12 (or nearest month-end available)
- 2019-12 (or nearest month-end available)
- 2020-12
- 2021-12
- 2022-12
- 2023-12
- 2024-12

For 2018–2019, actively seek multiple AMCs because older files may be unavailable, moved or scanned. Use Wayback captures as a fallback with the capture timestamp and original portfolio as-of date recorded separately. A Wayback copy is not equivalent to a verified original AMC-hosted file. For each year, seek at least two AMC sources where feasible; apply the fixed reduced-confidence rule when fewer than three eligible funds survive.

## Step 2 status

This plan changes the acquisition and reconciliation protocol, not the evidence status. No historical AMC portfolio file has yet been downloaded and hashed as part of this audit. No anchor set has been validated, no transition has been promoted from SAMPLE_ONLY, and no point-in-time membership intervals have been generated.

The first operational milestone is one genuine AMC-hosted portfolio file with preserved original bytes, a verified SHA-256, a separately stored parser output, and a reproducible ISIN-level equity set. That milestone validates acquisition/parsing only; it does not close Step 2.

Step 2 remains **OPEN / NOT COMPLETE**. Independent human review remains a mandatory acceptance gate; AI-assisted triage and source discovery are not human sign-off. Research hold and the prohibition on paper/live trading remain unchanged.
