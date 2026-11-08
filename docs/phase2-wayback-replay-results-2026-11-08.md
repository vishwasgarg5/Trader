# NIFTY 50 Wayback replay results — 2026-11-08

## Run and artifact provenance

- Pull request: https://github.com/vishwasgarg5/Trader/pull/37
- Successful acquisition replay: https://github.com/vishwasgarg5/Trader/actions/runs/42504090115
- Workflow run ID: `42504090115`
- Artifact: `nifty50-wayback-replay-pr-37` (artifact ID `13626891628`)
- Artifact report timestamp: `2026-11-08T17:16:44.502282+00:00`
- Run head used for replay: `7f53350f63f1ea27c1246d21a3c6787fad83621b`
- Current PR head after workflow cleanup: `2451bf09cbe34aefc2b4b6d86b0cc7576826a775`

## Acquisition outcome

The controlled replay completed successfully. CDX metadata was retrieved for all 18 targets, with 18 metadata records archived and no CDX query failures. Twelve constituent-snapshot captures were attempted.

Three captures passed all of the following checks:
- HTTP 200 from the Wayback replay endpoint;
- exact CDX Base32 SHA-1 digest verification;
- 50 distinct constituent symbols;
- valid ISIN on every row.

| Capture timestamp | Bytes | SHA-256 | Result |
|---|---:|---|---|
| 2018-05-30 10:17:25 | 2,938 | `1300ed616e536040b1379e1151383581bfe10c9fd100bb410e46f4a67f2e678d` | Candidate; digest verified |
| 2018-09-29 10:36:32 | 2,945 | `ab2ba82a0eb5e4deb890cec8ebecaf4644a4ca695ebc688dbaec4d580f14e236` | Candidate; digest verified |
| 2021-06-15 18:35:23 | 3,002 | `ebf5372eba6be1318abe3d6b143af2280bb8d996b41bee7ee8d8c7b47912f646` | Candidate; digest verified |

All three are classified `50_CONSTITUENT_SNAPSHOT_CANDIDATE_PENDING_REVIEW`. They are not canonical membership intervals.

## Cross-snapshot and transition-register comparison

### May to September 2018

The 2018-05-30 and 2018-09-29 verified snapshots differ by exactly:
- Added: `JSWSTEEL`
- Removed: `LUPIN`

This is consistent with the registered 2018-08-28 NIFTY 50 notice (effective 2018-09-28). The 2018-09-29 capture is one day after the stated effective date.

Both 2018 snapshots also show the February 2018 replacements in place: `BAJAJFINSV`, `GRASIM`, and `TITAN` are present, while `AMBUJACEM`, `AUROPHARMA`, and `BOSCHLTD` are absent. This is consistent with the registered 2018-02-21 notice effective 2018-04-02.

### June 2021

The 2021-06-15 verified snapshot has `TATACONSUM` present and `GAIL` absent, consistent with the registered 2021-02-23 NIFTY 50 replacement effective 2021-03-31.

These comparisons are corroborative snapshot checks only. Capture dates are not effective dates, and snapshot consistency does not replace the official notice, supersession screen, or independent review.

## Quarantined retrieval outcomes

Of the other nine attempted captures:
- Eight returned HTTP 429 from Wayback. No bytes were accepted for those attempts.
- One (2023-05-22) returned bytes whose computed CDX SHA-1 did not match the digest recorded for that capture. It remains quarantined; the code correctly rejected it.

The ZIP artifact also contains other CSV files already present in the checked-out branch. The three accepted outcomes above are counted from the run's `constituent_snapshots` report, not by counting every CSV in the ZIP.

## Safety and model state

- No membership register row was promoted.
- No point-in-time membership ledger was written.
- No prices, TRI, features, model parameters, holdout data, or trading state were changed.
- Pilot remains `RESEARCH_HOLD`; promotion and paper/live trading remain disabled.

## Next actions

1. Diagnose Wayback 429 handling with controlled retry/backoff and alternative replay endpoints while preserving CDX digest checks.
2. Investigate the 2023-05-22 digest mismatch without accepting or substituting bytes.
3. Continue quarterly coverage recovery and exact-date reconciliation.
4. Obtain independent human review before any candidate or transition row can be promoted.


## Follow-up replay with bounded HTTP 429 retries

A second replay was run after adding the bounded retry policy and regression test.

- Run: https://github.com/vishwasgarg5/Trader/actions/runs/42504385598
- Artifact: `nifty50-wayback-replay-pr-37` (artifact ID `13626872544`)
- Tested commit: `ad81099df2b6f30e446ca60e245332b073ff7067`
- Full Python test job: passed.
- Dedicated Wayback safeguard/replay job: passed.

The new artifact report records 12 targeted capture attempts:
- **10 digest-verified, structurally valid 50-constituent candidate snapshots**.
- **1 capture still blocked by HTTP 429** after three attempts (10s and 30s backoff).
- **1 capture (2023-05-22) rejected for CDX SHA-1 mismatch**. No bytes from this capture were accepted.

Two rate-limited captures that failed in the earlier replay now succeeded after bounded retries:
- 2024-05-24 — succeeded on attempt 3 after 10s and 30s waits.
- 2024-11-10 — succeeded on attempt 2 after a 10s wait.

The 10 candidates include a 2018-01-28 capture, which is outside the registered 2018-04-01 research window and must not be counted as an in-window quarter anchor. All candidate files remain PR artifacts; they have not been promoted into the main-branch snapshot inventory or canonical membership ledger.

The remaining 2024-08-19 HTTP 429 and 2023-05-22 digest mismatch remain quarantined. The successful run is an acquisition milestone only; it does not complete quarterly coverage, transition verification, or independent review.
