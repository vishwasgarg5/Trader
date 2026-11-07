# Nifty 50 pilot — security identity readiness (Step 3)

Status: **IN_PROGRESS — evidence not verified**

This step establishes controls for effective-dated identity continuity. It does not certify any current or historical mapping and does not authorize stitching price series.

## Required identity evidence

Every mapping must identify:
- a unique alias record;
- alias and official exchange symbols;
- a stable security identifier (ISIN/security-master key) for verified mappings;
- relation type: same-security ticker rename, vendor alias, or separate security;
- non-overlapping effective dates;
- HTTPS primary-source URL and archived source document with matching SHA-256;
- named independent reviewer and ISO review date for every row marked VERIFIED.

A separate security must retain its own identity. It must not be concatenated into another issuer/security's historical price series.

## Corporate-action boundary

The corporate-action ledger's evidence-integrity result is not proof of adjusted-price correctness. Split, bonus, rights, merger, demerger, dividend and symbol-change treatment must be reconciled against official terms and vendor OHLCV. A missing adjustment factor remains unresolved; it is never silently replaced with 1.

## Current repository state

- `security_symbol_aliases.csv` contains three unverified identity records; none is promoted to VERIFIED by this change.
- LTIM/LTM and Tata Motors/TMPV/TMCV identity distinctions remain subject to archived-source and independent review.
- The corporate-action ledger contains source-note evidence but explicitly does not establish adjusted-price correctness.
- The membership interval ledger is still empty, so Step 2 remains blocked and this step cannot be considered complete.

## Acceptance criteria

1. Verified aliases require stable security identity, source URL, archived evidence and matching digest.
2. Verified aliases require reviewer identity and a valid ISO review date.
3. Same-symbol and separate-security semantics remain distinct.
4. Overlapping mappings to different securities fail closed.
5. Corporate-action evidence validity never implies price adjustment verification.
6. No historical data is fabricated and no price series is stitched solely from ticker similarity.

## Safety

Research-only. No holdout access, evaluation authorization, promotion, paper trading or live execution is enabled.
