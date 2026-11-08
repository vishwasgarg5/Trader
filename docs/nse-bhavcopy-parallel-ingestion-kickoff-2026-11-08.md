# NSE bhavcopy parallel-ingestion kickoff

The four representative archive dates already passed the earlier NSE archive-access probe. This work adds a reproducible parser/acquirer for the full cash-market daily bhavcopy, with raw ZIP SHA-256, ZIP CRC, expected date, EQ series, ISIN, OHLC, previous close, volume and turnover checks.

The first sample uses exact dates already present in the acquired NIFTY 50 TRI source:
- 2018-01-02 (legacy CM archive format)
- 2020-03-19 (legacy CM archive format)
- 2024-07-05 (last day before the UDiFF archive cutover)
- 2024-07-08 (UDiFF archive format)

The calendar manifest builder verifies each underlying half-year TRI source JSON against the SHA-256 recorded in the TRI register. These dates are labelled `CANDIDATE_UNREVIEWED_TRI_OBSERVATION`; the TRI source itself remains pending independent review. The downloader rejects candidate dates by default. The sample workflow must explicitly pass `--allow-candidate-calendar`, and the report is a research-only sample. This does not certify the 2018-2024 trading calendar.

Run locally:

```bash
python scripts/build_nse_bhavcopy_calendar_manifest.py --dates 2018-01-02,2020-03-19,2024-07-05,2024-07-08 --output data/tmp/nse_bhavcopy_sample_calendar.csv
python scripts/acquire_nse_bhavcopy.py --calendar-manifest data/tmp/nse_bhavcopy_sample_calendar.csv --allow-candidate-calendar --output-dir data/tmp/nse_bhavcopy_sample --report data/reports/nse_bhavcopy_sample_report.json
```

The sample workflow uploads only the summary report, not raw market-data files. Do not commit or redistribute the raw files until NSE data licensing and retention permissions are confirmed. Full-period ingestion requires a reviewed, complete exchange-session calendar, including ad-hoc closures and special sessions, and should then run in bounded resumable chunks.
