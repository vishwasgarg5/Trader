# NSE archive access feasibility probe

Status: **PROBE IMPLEMENTED; LIVE RETRIEVAL NOT YET RUN**.

## Why this probe exists

The pilot needs daily equity bhavcopy inputs for 2018–2024 and primary Nifty 50 membership notices. Public archive discoverability is not proof that historical bytes are still served, that every trading day is covered, or that use/redistribution is unrestricted.

Official NSE's [All Reports page](https://www.nseindia.com/all-reports) currently exposes the full bhavcopy and the CM-UDiFF Common Bhavcopy Final ZIP. It also labels the legacy CM Bhavcopy CSV / Common Bhavcopy CSV reports as discontinued from 8 July 2024, with the UDiFF report replacing them. The page exposes historical daily/monthly report selectors. The [NSE paid EOD/historical data page](https://www.nseindia.com/static/market-data/eod-historical-data-subscription) separately describes subscription-based EOD binary files and historical trade data; this is distinct from testing public daily bhavcopy ZIP downloads.

The old daily archive URL convention and the new UDiFF filename convention are recorded in the probe, but a convention is not evidence that a particular historical file is available. The legacy URL convention has been described by a third-party technical reference; the actual access result must come from the live probe.

## Bounded live test

Run the manual GitHub Actions workflow **NSE archive access probe**. It makes seven unauthenticated GET requests and stores only a JSON evidence artifact (not the market files):

| Sample | Expected source | What it tests |
|---|---|---|
| 2018-01-02 | Legacy NSE CM bhavcopy ZIP | Early-window daily price/turnover archive |
| 2020-03-19 | Legacy NSE CM bhavcopy ZIP | Mid-window access and 2020 transition date |
| 2024-07-05 | Legacy NSE CM bhavcopy ZIP | Last session before format cutover |
| 2024-07-08 | NSE CM-UDiFF ZIP | First session at the new-format boundary |
| 2018-02-21 | Nifty Indices constituent-change PDF | Early-window primary membership notice |
| 2020-03-16 | Nifty Indices superseding notice PDF | 2020 accelerated replacement chain |
| 2024-08-23 | Nifty Indices constituent-change PDF | Recent-window primary membership notice |

For ZIPs, the probe checks HTTP status, byte count, SHA-256, ZIP CRC, presence of a CSV member, and a non-empty CSV header. For PDFs, it checks HTTP status, byte count, SHA-256, and the PDF magic signature. It uses no credentials, makes no bulk request, retains no downloaded market files, and enforces a 25 MiB response cap.

## Interpretation and limits

- A successful sample means only that the exact URL returned parseable public bytes at probe time without credentials.
- A failed sample is a source-access blocker to investigate (404, access denial, bot protection, wrong filename, format drift, or network failure); it is not proof the entire archive is unavailable.
- Four bhavcopy samples do not establish complete daily coverage for 2018–2024. After this pilot, build a trading-calendar coverage manifest and test every required date or a statistically justified, predeclared coverage plan.
- Three notice PDFs do not establish full circular/press-release archive completeness. Reconcile all candidate URLs, superseding chains, OCR-only items and missing source documents.
- Public access is not a data licence. Confirm NSE/Nifty Indices terms and redistribution restrictions before committing raw data to the repository or another hosted system.
- This probe does not test Nifty 50 TRI historical completeness. The official [Nifty Indices historical reports page](https://www.niftyindices.com/reports) exposes a separate Total Returns Index Values report; daily coverage and export limits still require a separate date-range test.
- It does not change membership ledgers, price/benchmark datasets, protocol permissions, evaluation or holdout status.

## Protocol status

No source-coverage gate is changed by implementing or passing the probe. Step 2 membership remains blocked; Steps 3–5 retain their evidence blockers; Step 6 labels remain disabled until upstream evidence passes.
