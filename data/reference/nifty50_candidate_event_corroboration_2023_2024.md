# Independent exchange corroboration — NIFTY 50 candidate events (2023–2024)

Research branch evidence note. This is a corroboration log, not a human sign-off and not authority to populate verified membership intervals.

## 1. HDFC out / LTIM in — effective 2023-07-13 (close 2023-07-12)

- Primary NSE Indices press release (2023-07-04): https://nsearchives.nseindia.com/web/sites/default/files/2023-07/ind_prs04072023.pdf
- Primary source already archived in this repository: `data/reference/source_documents/NOTICE-N50-NOTICE-2023-07-04.pdf`; the transition register records SHA-256 `dbc48cbd8b127ca35df4fbac956964dc0922d282baab25956025beb20ba65cb0`.
- Corroborating NSE Futures & Options circular: NSE/FAOP/57427, Circular 113/2023, dated 2023-07-04. The retrieved copy is hosted by a third-party circular mirror, not the NSE archive: https://download.latinmanharlal.com/downloads/LM-SPAN-MARGIN/2324/NSE_Circulars/etc/Change%20in%20the%20Constituents%20of%20Indices.pdf
- The circular identifies the same NIFTY 50 HDFC exclusion and LTIM inclusion, with the same 2023-07-13 effective date. The official NSE-hosted circular bytes have not yet been located/archived/hashed in this repository. Treat this as corroborating document content, but retain the archive-provenance gap.

## 2. UPL out / SHRIRAMFIN in — effective 2024-03-28 (close 2024-03-27)

- Primary NSE Indices press release: https://www.niftyindices.com/Press_Release/ind_prs28022024.pdf
- Primary source already archived: `data/reference/source_documents/NOTICE-N50-NOTICE-2024-02-28.pdf`; transition register records SHA-256 `5c70d043edde682a31fc5fa043a3b829a380fc9896de904bcb76d64b8319f698`.
- Corroborating NSE Futures & Options circular (official NSE archive): NSE/FAOP/60909, Circular 24/2024, dated 2024-02-28: https://nsearchives.nseindia.com/content/circulars/FAOP60909.pdf
- The circular independently repeats UPL exclusion and SHRIRAMFIN inclusion in NIFTY 50 and the same effective point. Its PDF is located on the official NSE archive but is not yet committed or SHA-256 recorded in this repository.

## 3. DIVISLAB and LTIM out / BEL and TRENT in — effective 2024-09-30 (close 2024-09-27)

- Primary NSE Indices press release: https://nsearchives.nseindia.com/web/sites/default/files/2024-08/ind_prs23082024.pdf
- Primary source already archived: `data/reference/source_documents/NOTICE-N50-NOTICE-2024-08-23.pdf`; transition register records SHA-256 `efc8eab5d129eaa2219e10b57ab9a5c3ce2d0cd7b8c5ebd2c7b6bc244a38b2b8`.
- Corroborating NSE Futures & Options circular (official NSE archive): NSE/FAOP/63556, Circular 102/2024, dated 2024-08-24: https://nsearchives.nseindia.com/content/circulars/FAOP63556.pdf
- The circular repeats both exclusions and both inclusions with the same 2024-09-30 effective point.
- Supersession check: NSE/FAOP/64175, Circular 114/2024, dated 2024-09-26: https://nsearchives.nseindia.com/content/circulars/FAOP64175.pdf. It updates only Nifty Midcap Select effective timing, not the NIFTY 50 changes. This is consistent with retaining the 2024-08-23 flagship NIFTY 50 event dates.

## Status and remaining controls

- Candidate symbols, actions, announcement dates and effective dates are corroborated by the primary NSE Indices releases and, for all three cases, a separate NSE F&O circular document. For the July 2023 circular, the retrieved copy is currently only from a third-party mirror; official-host verification is still required.
- The three primary NSE Indices PDFs are already archived and hashed in the repository's transition register. The corroborating F&O circular PDFs are not yet archived/hashed here.
- This work does not independently reconcile year-end constituent snapshots, establish complete notice coverage, resolve the temporary JIOFIN episode, or authenticate every historical interval.
- All transition rows remain `SAMPLE_ONLY`; reviewer and reviewed-at fields remain blank. Do not promote events or populate `nifty50_membership.csv` until a human reviewer checks the original documents, official archive provenance, symbol identities, effective-close convention and dated constituent snapshots.
- Research/promotion gate remains closed. No production or trading approval is implied.
