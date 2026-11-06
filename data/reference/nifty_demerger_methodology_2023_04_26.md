# Nifty equity-index demerger methodology control (26 April 2023)

- Issuer: NSE Indices Limited
- Publication date: 2023-04-26
- Official source: https://www.niftyindices.com/Press_Release/ind_prs26042023.pdf
- Applicability: schemes of arrangement involving demerger approved by equity shareholders on or after 2023-04-30
- Source status: official release located and text reviewed. Original PDF bytes could not be downloaded into this repository during this run; no local source hash is claimed. Independent review remains pending.

## Relevant methodology summarized from the official release

Where an exchange conducts a special pre-open session (SPOS) for the demerging security, the demerged company is retained and the spun-off entity is included in the index at a constant price derived from the parent security's prior close and the SPOS price discovery.

The spun-off entity is subsequently removed after listing under the methodology's price-band observation rules. The 2023 JIOFIN event must therefore be represented as multiple identity states:
- pre-demerger parent constituent;
- temporary dummy/spun-off index constituent with a methodology-derived constant price;
- listed JIOFIN security after listing;
- exclusion from the index at the effective close specified by the later notice.

If SPOS is not conducted, the methodology prescribes a different removal/replacement treatment. Do not apply the SPOS branch generically to every demerger.

## Audit requirements

1. Preserve the original notice and methodology version applicable on the event date.
2. Store dummy-symbol and listed-security identity mappings as distinct effective-dated states.
3. Preserve the constant-price calculation inputs and derived value with source provenance.
4. Verify each price-band observation from authoritative exchange records; do not infer it from a press-release conditional.
5. Keep publication date separate from effective date and record the close convention.
6. This methodology note does not establish complete annual notice coverage or prove any membership interval independently verified.

**Status:** LOCATED_NOT_ARCHIVED; source hash and independent review pending.
