# Nifty 50 notice triage rubric

Status: **IMPLEMENTED AS A CONSERVATIVE REVIEW QUEUE; NO NOTICE IS HUMAN-VERIFIED BY AUTOMATION**.

## Scope and baseline

The input is the 687-row broad NSE/Nifty Indices archive inventory for 2018–2024. It is a discovery/control inventory, not a complete or authoritative list of Nifty 50 membership events. The triage tool does not change source rows, review states, transition records, membership intervals, or research permissions.

Initial inventory states on the current main revision:
- 570 `DISCOVERED_UNREVIEWED` / `UNCLASSIFIED_REVIEW_REQUIRED` rows.
- 97 rows already screened as no flagship Nifty 50 change or fixed-income scope; these remain pending independent human sign-off.
- 20 `CANDIDATE` rows; these are not verified transitions.

## Decision rubric

| Triage category | Rule | Required human action |
|---|---|---|
| `MEMBERSHIP_OR_EFFECTIVE_DATE_REVIEW` | A recorded candidate, inclusion, exclusion, temporary constituent, superseding, deferral, or effective-date effect | Inspect the full primary-source notice chain; record security, action, original and final effective dates, and cited source |
| `OUT_OF_SCOPE_CANDIDATE_HUMAN_SIGNOFF` | Existing scope screen explicitly identifies no flagship Nifty 50 constituent change or fixed-income-only scope | Confirm the source document identity and scope; record why it cannot affect Nifty 50 membership |
| `UNRESOLVED_REVIEW_REQUIRED` | Unclassified, missing, ambiguous, conflicting, OCR-only, or incomplete source evidence | Retrieve/inspect the primary document or retain unresolved with a specific reason |

The tool deliberately does not create an automatic “verified” category. Every row is marked `human_review_required=true` and `human_signoff_status=PENDING`. A screen is not a sign-off.

## Per-row review record

The generated queue retains notice ID, announcement/effective dates, observed effect, official source URL, local archive path, SHA-256, and existing review state. It adds:
- `triage_category` and a deterministic reason.
- `human_signoff_status` (initially `PENDING`).
- `reviewer_name`, `review_date`, and `review_decision_reason` fields for a separately controlled review process.

A reviewer decision must additionally cite the primary document and confirm that the archived bytes match the source URL and recorded SHA-256. If the notice supersedes or defers another notice, the full chain must be considered. A notice naming another Nifty index is not evidence of a Nifty 50 change.

## Special review cases

- **March 2020 YESBANK / SHREECEM:** preserve the March 19 Nifty 50 effective event as a candidate while reviewing the February 18, March 16, March 23, March 25 and May 13 chain. Later general deferments must not be applied mechanically to an already-effective Nifty 50 event. Human sign-off remains pending.
- **Strides Pharma (December 2, 2024):** source-identity mismatch remains blocked. Do not infer document contents from a different same-date PDF or classify it as an exclusion.
- Any missing PDF, mismatched URL/hash, OCR-only interpretation, uncertain entity identity, or conflict between notices remains unresolved.

## Outputs and safety

Run `python -m trader.nifty50_notice_triage` to produce:
- `data/reports/nifty50_notice_triage.csv` — row-level review queue.
- `data/reports/nifty50_notice_triage.json` — category counts and yearly breakdown.

These are generated reports, not authoritative source ledgers. The triage is diagnostic only: `membership_written=false`, and no evaluation, holdout, paper-trading, or live-trading permission is changed.

## Official data access feasibility note

The official Nifty Indices historical reports page exposes a “Total Returns Index Values” report and a CSV output for Total Returns Index / Net Total Returns Index. This is the appropriate primary-source starting point for the Nifty 50 TRI series, but the public page alone does not establish that every daily observation for 2018–2024 can be retrieved without account, request, or rate limits.

The official NSE “All Reports” page exposes daily/monthly report archives and historical index/total-return data selectors, while the Nifty Indices press-release archive exposes historical notice listings. These public interfaces establish discoverability, not complete downloadable coverage of every notice PDF or a verified historical constituent snapshot for every semi-annual boundary. Coverage must be tested year-by-year and recorded from actual downloaded files; no completeness claim is made here.
