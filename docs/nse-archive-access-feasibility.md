# NSE archive access feasibility probe

Status: **REPRESENTATIVE PUBLIC ACCESS CONFIRMED; FULL-PERIOD COVERAGE NOT PROVEN**.

## Why this probe exists

The pilot needs daily equity bhavcopy inputs for 2018–2024 and primary Nifty 50 membership notices. Public archive discoverability is not proof that historical bytes are still served, that every trading day is covered, or that use/redistribution is unrestricted.

Official NSE's [All Reports page](https://www.nseindia.com/all-reports) currently exposes the full bhavcopy and the CM-UDiFF Common Bhavcopy Final ZIP. It also labels the legacy CM Bhavcopy CSV / Common Bhavcopy CSV reports as discontinued from 8 July 2024, with the UDiFF report replacing them. The page exposes historical daily/monthly report selectors. The [NSE paid EOD/historical data page](https://www.nseindia.com/static/market-data/eod-historical-data-subscription) separately describes subscription-based EOD binary files and historical trade data; this is distinct from testing public daily bhavcopy ZIP downloads.

The old daily archive URL convention and the new UDiFF filename convention are recorded in the probe, but a convention is not evidence that a particular historical file is available. The legacy URL convention has been described by a third-party technical reference; the actual access result must come from the live probe.

## Bounded live test

Run the GitHub Actions workflow **NSE archive access probe** (automatically on changes to the probe; also manually dispatchable). The first live run on 2026-11-07, commit `50d5d75259e3ed43a5fbd241d4b1c14e210df7f1`, passed all seven unauthenticated GET checks: four bhavcopy ZIPs and three Nifty Indices membership-notice PDFs. Run: [#42386319035](https://github.com/vishwasgarg5/Trader/actions/runs/42386319035). It stores a JSON evidence artifact (not the market files):

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

## Observed result — 2026-11-07\n\n| Sample | HTTP | Bytes | SHA-256 | Result |\n|---|---:|---:|---|---|\n| 2018-01-02 legacy bhavcopy | 200 | 69,476 | `73976825d277dc7f2d8e3ce6cac4dd8d3e795f296c031acc7a38528fd4700bb7` | ZIP CRC + CSV header valid |\n| 2020-03-19 legacy bhavcopy | 200 | 70,621 | `9c590311f613e0c1f33d07ab52a3ba4426bd867ac3a258f7dce38748d6db55b7` | ZIP CRC + CSV header valid |\n| 2024-07-05 legacy bhavcopy | 200 | 109,203 | `e08c8c0650e6807f8b1abd0658bc8d87cbe2d78c2fc77e05c82878f30be46665` | ZIP CRC + CSV header valid |\n| 2024-07-08 UDiFF bhavcopy | 200 | 166,236 | `0ef55b77c30c8a57d5451cd371424242ad515f708630736ea6dc44c38d6e1e85` | ZIP CRC + CSV header valid |\n| 2018-02-21 membership notice | 200 | 575,624 | `a31019896822ef7a28f2229ba5e1552c835f51952ee033d02a5f79c9c7914b3d` | PDF signature valid |\n| 2020-03-16 superseding notice | 200 | 686,103 | `4e7726fa8bfe5dc12f2b42121f69fd29bc7ec1da01c2c26dae84f2f3fe8e9f37` | PDF signature valid |\n| 2024-08-23 membership notice | 200 | 788,856 | `efc8eab5d129eaa2219e10b57ab9a5c3ce2d0cd7b8c5ebd2c7b6bc244a38b2b8` | PDF signature valid |\n\nThis establishes public unauthenticated retrieval for representative bhavcopy dates from the start, middle, and end of the legacy period, plus the first UDiFF date, and for three official Nifty Indices membership notices. The 2018 and 2020 bhavcopy headers expose `TOTTRDVAL`; the UDiFF header exposes `TtlTrfVal`, so traded value is present but requires a format-specific parser.\n\n**Important boundary:** the PDF samples are Nifty Indices press releases, not a comprehensive test of the separate NSE member-circular archive. General NSE circular coverage back to 2018 remains unproven.\n\n## Interpretation and limits

- A successful sample means only that the exact URL returned parseable public bytes at probe time without credentials.
- A failed sample is a source-access blocker to investigate (404, access denial, bot protection, wrong filename, format drift, or network failure); it is not proof the entire archive is unavailable.
- Four bhavcopy samples do not establish complete daily coverage for 2018–2024. After this pilot, build a trading-calendar coverage manifest and test every required date or a statistically justified, predeclared coverage plan.
- Three notice PDFs do not establish full circular/press-release archive completeness. Reconcile all candidate URLs, superseding chains, OCR-only items and missing source documents.
- Public access is not a data licence. Confirm NSE/Nifty Indices terms and redistribution restrictions before committing raw data to the repository or another hosted system.
- This probe does not test Nifty 50 TRI historical completeness. The official [Nifty Indices historical reports page](https://www.niftyindices.com/reports) exposes a separate Total Returns Index Values report; daily coverage and export limits still require a separate date-range test.
- It does not change membership ledgers, price/benchmark datasets, protocol permissions, evaluation or holdout status.

## Protocol status

No source-coverage gate is changed by implementing or passing the probe. Step 2 membership remains blocked; Steps 3–5 retain their evidence blockers; Step 6 labels remain disabled until upstream evidence passes.
