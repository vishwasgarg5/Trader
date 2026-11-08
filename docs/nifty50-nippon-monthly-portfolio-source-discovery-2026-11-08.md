# NIFTY 50 monthly portfolio disclosure source discovery

Date: 2026-11-08  
Research branch: `research/nifty50-wayback-acquisition-2026-11-08`  
PR: #36

## Source identified

Nippon India Mutual Fund's official "Factsheet, Portfolio and Other Disclosures" archive lists monthly scheme-portfolio workbooks back to January 2018. The scheme, Nippon India Index Fund - Nifty Plan (renamed Nifty 50 Plan), is explicitly a Nifty 50 tracking index fund. Official factsheets show the fund's Nifty 50 TRI benchmark and the stated replication objective.

Official source pages:
- https://mf.nipponindiaim.com/investor-service/downloads/factsheet-portfolio-and-other-disclosures/
- https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Index-Fund-Nifty-50-Plan.aspx

A July 2020 official factsheet identifies the Nifty-tracking scheme and gives its portfolio as of 2020-06-30. The factsheet aggregates "Equity Less Than 1% of Corpus", so the factsheet PDF alone is not sufficient to establish the complete 50-stock list. Use the monthly portfolio workbook, not the PDF factsheet, for any constituent comparison.

## First machine probe

The official archive's 2024-12 monthly workbook link resolves to:

`https://mf.nipponindiaim.com/InvestorServices/FactsheetsDocuments/NIMF-MONTHLY-PORTFOLIO-31-Dec-24.xls`

Workflow `NIFTY 50 Nippon monthly portfolio source probe` downloads this single workbook, validates OLE .xls format, records HTTP metadata and SHA-256, and inventories sheets and rows containing "Nifty". It uploads the original workbook and report as a temporary artifact only.

## Evidence rules

- Keep the portfolio's as-of date separate from its publication/download date.
- Extract only the exact Nifty 50 tracking scheme, not other Nippon funds or ETFs.
- Preserve security names, ISINs, quantities, weights, cash, receivables and derivative lines separately.
- A fund portfolio is corroborative, not a direct index constituent record: cash, receivables, sampling and tracking differences can exist.
- Require 50 distinct equity constituents and compare to independent NSE Indices/Wayback anchors before using it as a quarterly checkpoint.
- Do not promote holdings to canonical membership or model inputs without primary-source review and human sign-off.
- This probe is source/schema discovery only. It does not authorize a second AMC or alter the existing AMC experiment scope.
