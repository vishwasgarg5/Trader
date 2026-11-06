# Point-in-time Nifty 50 membership data dictionary

These files define the evidence schema for reconstructing the Nifty 50 research universe from 2018-04-01. They intentionally contain headers only: no historical membership has been inferred or fabricated.

## Files

- `data/reference/nifty50_notice_register.csv`: inventory of every official index notice screened, including notices that do not affect Nifty 50 and notices that supersede, defer, or cancel earlier notices.
- `data/reference/nifty50_membership.csv`: effective-dated membership intervals.
- `data/reference/symbol_identity_ledger.csv`: effective-dated continuity between exchange symbols and security identities.

## Membership interval semantics

- `valid_from` is inclusive.
- `valid_to` is exclusive; blank means the interval is open-ended.
- Dates use ISO 8601 `YYYY-MM-DD`.
- Each row represents one security identity's membership interval, not merely a ticker string.
- A ticker rename must not create a false exit and re-entry if the underlying security identity is continuous.
- A merger, demerger, replacement, temporary inclusion, deferral, or cancellation must be represented according to the official effective notice and documented identity mapping.

## Evidence requirements

Every membership row must reference a notice or authoritative constituent snapshot. Preserve the original source document in the repository (or an immutable, access-controlled evidence store), record its SHA-256, and retain the original source URL and publication/effective dates.

The notice register must include all screened notices, including negative screens. A notice cannot be omitted merely because it does not list Nifty 50. Record cancellation, supersession, and deferment relationships explicitly.

## Verification states

Use only these controlled values:

- `UNVERIFIED`: entered but not independently checked.
- `VERIFIED`: source and interpretation checked by a named reviewer.
- `REJECTED`: source or interpretation invalid; explain in notes.
- `SUPERSEDED`: replaced by a later official notice; retain the relationship.

A source hash proves file identity, not source authenticity or correct interpretation.

## Acceptance checks before coverage can pass

1. The complete annual and ad-hoc notice inventory for the period is reviewed.
2. Supersession, cancellation, and deferment chains are resolved.
3. Effective-dated membership is reconciled against authoritative snapshots.
4. Every interval has an auditable source and independent reviewer.
5. For every trading date, exactly 50 constituents are represented, subject only to documented index-event timing conventions.
6. Every historical constituent has a corresponding security identity and price-history coverage, or an explicit adjudicated exception.
7. No year is marked complete based on a partial notice screen.

Do not set the integrity report's point-in-time membership flag to true based on non-empty CSVs, row counts, or hashes alone.
