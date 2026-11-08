# NIFTY 50 Phase 2 — historical anchor matching kickoff

Date: 2026-11-08
Branch: `research/nifty50-wayback-acquisition-2026-11-08`
Input head: `001c4f966f952ef82214ad6d794b4e2611285a52`
PR: #36

## Phase 2 objective

Reconcile the available point-in-time NIFTY 50 candidate snapshots against dated primary NSE Indices notices and independent corroboration. This phase does not authorize canonical membership changes, model fitting on unverified membership, holdout access, or trading.

## Machine-generated packet inspected

The successful `NIFTY 50 anchor matching packet` workflow (run 40, run ID `42501576615`) produced artifact `nifty50-anchor-matching-review-packet`.

Packet summary:
- 17 candidate anchors across 2018-Q1 through 2024-Q4.
- 16 adjacent-anchor comparisons.
- 34 observed symbol additions/removals.
- All 34 observed changes have a corresponding row in the existing transition register.
- Zero observed changes without a register candidate.
- Zero registered events not visible in the adjacent-anchor differences.
- All 16 pair comparisons remain `REVIEW_REQUIRED`.
- All 17 anchors remain `CANDIDATE_PENDING_HUMAN_REVIEW`.
- All 34 register rows retain `SAMPLE_ONLY`; no row was promoted.

The 2018-Q1 anchor predates the registered research window start (2018-04-01). It is contextual only and cannot establish an in-window membership state.

## First primary-source reconciliation started

The archived extracted text for the official IISL press release dated 2018-02-21 states that the following NIFTY 50 changes become effective 2018-04-02 (after the 2018-03-28 close):

| Action | Symbol |
|---|---|
| REMOVE | AMBUJACEM |
| REMOVE | AUROPHARMA |
| REMOVE | BOSCHLTD |
| ADD | BAJAJFINSV |
| ADD | GRASIM |
| ADD | TITAN |

The six symbols and actions agree with the first adjacent-anchor difference (2018-Q1 to 2018-Q2) and the six existing transition-register candidates. Source URL: https://www.niftyindices.com/Press_Release/ind_prs21022018.pdf . Extracted text path: `data/reference/extracted_notice_text/N50-NOTICE-2018-02-21.txt`.

**Disposition:** automated primary-text/anchor/register consistency check = MATCH for these six rows. Existing verification status remains `SAMPLE_ONLY`; reviewer and independent sign-off are still blank/pending. The extracted text is not a substitute for a second-person review of the source PDF and its hash/supersession chain.

## Required follow-up queue

1. Independently review the 2018-02-21 source PDF, archived hash, notice supersession status, and six transition rows; record human reviewer sign-off only when actually completed.
2. Repeat notice-to-anchor matching chronologically for the remaining candidate transition groups.
3. Investigate security identity/ISIN changes separately from constituent additions/removals, including TATAMOTORS/TMPV lineage.
4. Resolve the previously reported CDX/download digest anomalies before relying on affected snapshots. A packet row marked candidate is not permission to ignore any unresolved acquisition-state anomaly.
5. Use NSE bhavcopy and AMC portfolio data only as corroboration; neither substitutes for the official index notice.
6. Keep missing notices, broad event windows, ambiguous identity changes, and unsupported events explicitly unresolved.

## Non-promotion and safety controls

- No changes to `data/reference/nifty50_membership.csv`, the canonical identity ledger, membership intervals, model inputs, or holdout.
- No promotion of `SAMPLE_ONLY` rows.
- NIFTY 50 remains the sole pilot universe; no NIFTY 200/500 expansion.
- Pilot GO, if ever earned, means eligibility for a broader test only—not paper-trading or live-trading permission.
- PR #36 remains open/unmerged; `main` remains untouched.
