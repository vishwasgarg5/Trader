# NIFTY 50 anchor matching and parallel bhavcopy kickoff

Date: 2026-11-08  
Branch: `research/nifty50-wayback-acquisition-2026-11-08`  
PR: #36

## Decision

Start the reconciliation stage from the 16 currently usable Wayback quarterly snapshots. Do not wait for all 28 quarters before preparing comparisons. The 16 snapshots are still supplementary candidate anchors, not approved point-in-time membership facts. The 2018-Q1 anchor predates the registered research window start (2018-04-01) and is used only as a possible seed after review.

## Anchor matching packet

Run:

```bash
python scripts/build_nifty50_anchor_matching_packet.py
```

The script:
- re-reads every candidate file from the acquisition state;
- requires local SHA-256 and decoded CDX Base32 SHA-1 to match the exact bytes;
- requires the existing state to mark the capture `MATCH` and the CSV to contain exactly 50 distinct symbols;
- selects one latest candidate per quarter and retains alternates in the report;
- compares adjacent anchor symbol sets;
- brackets existing transition-register rows by their effective dates;
- reports observed changes with a register candidate, unexplained observed changes, and registered events not visible between the anchors.

All transition-register statuses are carried through unchanged. A `SAMPLE_ONLY` row is never upgraded by a symbol-set match. The output is a review packet only and never writes `nifty50_membership.csv`, the identity ledger, annual coverage, or model inputs.

## Digest mismatch diagnosis

Run the bounded manual diagnostic workflow **NIFTY 50 Wayback digest diagnostics**. It:
1. decodes each CDX digest to the 20-byte SHA-1 value before comparing;
2. re-queries CDX with the `type` field so revisit metadata is visible when supplied;
3. fetches the exact capture twice and the nearest neighbouring capture with the same digest, where available;
4. records byte count, HTTP status, memento headers, capture type, and recomputed digest.

No mismatch is accepted by the diagnostic. Acceptance still requires a fetched body to match its CDX digest; otherwise the capture remains quarantined and another independently verified capture must cover the quarter.

## Three unresolved notice PDFs

The 2018-06-05, 2019-07-16 and 2023-03-14 notice records remain `NOT_YET_RESOLVED` while their CDX queries are incomplete or transiently failing. HTTP 503 and empty incomplete searches are not proof of absence. Retry after backoff; do not let these records block anchor comparisons or independent market-data ingestion.

## Parallel NSE bhavcopy ingestion

Run only with a reviewed, source-hashed date manifest:

```csv
trade_date,calendar_source_url,calendar_source_path,calendar_source_sha256
```

Then:

```bash
python scripts/acquire_nse_bhavcopy.py --calendar-manifest PATH_TO_REVIEWED_MANIFEST
```

The downloader uses the legacy NSE CM ZIP convention through 2024-07-05 and UDiFF from 2024-07-08. It verifies ZIP CRC, CSV schema, trade date, EQ-series ISIN, OHLCV, and turnover, then stores raw ZIP bytes content-addressed and parsed rows separately. It deliberately does not infer trading dates from weekdays. A source-backed 2018-2024 holiday/session calendar must be prepared before a full-period run.

The existing archive access probe has already demonstrated public ZIP access for representative dates (2018-01-02, 2020-03-19, 2024-07-05 and 2024-07-08). This is not full daily coverage. Confirm data licensing and repository-retention rights before committing raw market files.

## Release boundary

- NIFTY 50 remains the only pilot universe.
- No NIFTY 200/500 expansion.
- No membership interval is promoted by this work.
- Model validation remains HOLD until the machine-verified ledger and independent reviewer sign-off are complete.
- No holdout, paper-trading, promotion or live-trading permission changes.
