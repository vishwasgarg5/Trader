# NIFTY 50 pilot — holiday calendar independent review packet

Experiment: `NIFTY50_PILOT_001`  
Scope: NIFTY 50 only; TRI calendar evidence for 2018-01-01 through 2024-12-31.  
Generated: 2026-11-08  
Status: **REVIEW REQUIRED — NOT CERTIFIED**

## Contents

- `data/reference/nifty50_tri_holiday_review_register.csv`: 132 machine-extracted annual holiday candidates with blank independent-review fields.
- Annual circular archive manifest: `data/reports/nifty50_tri_holiday_circular_archive.json`.
- Text extraction report: `data/reports/nifty50_tri_holiday_extraction.json`.
- Holiday/TRI gap diagnostic: `data/reports/nifty50_tri_holiday_reconciliation.json`.
- Ad-hoc closure register and archive manifest: `data/reference/nifty50_tri_ad_hoc_closures.csv`, `data/reports/nifty50_tri_ad_hoc_closure_archive.json`.
- Seven special-session circulars and register: `data/reference/nifty50_tri_weekend_session_review.csv`, `data/reports/nifty50_tri_weekend_circular_archive.json`.

## Required independent-review procedure

1. Reviewer obtains each PDF from the official NSE archive independently (not from the repository copy alone).
2. Compare the independently obtained PDF's SHA-256 and circular reference to the archive manifest. If bytes differ, preserve both copies and investigate; do not overwrite.
3. Visually inspect each PDF page containing the holiday table. Compare every extracted row with the source, including dates, weekday, holiday description, segment, weekday/weekend classification, and special-session notes.
4. Review superseding and ad-hoc circulars, particularly `NSE/CMTR/57285` (2023 Bakri Id moved from 28 June to 29 June), `NSE/CMTR/40536` (29 April 2019), and `NSE/MSD/42319` (21 October 2019).
5. Review all seven weekend/special-session circulars separately. A weekend date may be a genuine trading session; never auto-delete it.
6. Fill reviewer decision, reviewer name, UTC timestamp, and notes in the CSV. Attach a signed review memo and record reviewer identity/qualification.
7. Only a separately authorized maintainer may update source rows to `VERIFIED` after review. Automation must not invent reviewer identity or sign-off.

## Current automated diagnostics (not a reviewer conclusion)

- 7 annual circulars archived for 2018–2024.
- 132 extracted candidate date rows; 0 weekday mismatch flags and 0 missing source weekdays.
- 39 TRI gaps longer than 3 calendar days; the current diagnostic identifies 0 unexplained weekdays after including two 2019 ad-hoc closures and the 2023 holiday revision.
- Seven weekend-dated TRI observations have corresponding special-session circulars archived.
- The 2023 revision circular PDF is available from a third-party mirror. It is not an official-host archive copy, and the mirror does not independently establish authenticity.
- Source semantics, calendar completeness, and independent sign-off remain pending.

## Prohibited shortcuts

Do not mark the calendar complete based solely on weekday agreement, gap explanation, PDF signature, or SHA-256. Hashes establish byte integrity only. Do not alter TRI values to fit the calendar. Do not access the holdout, run model evaluation, promote, paper trade, or execute live trades as part of this review.
