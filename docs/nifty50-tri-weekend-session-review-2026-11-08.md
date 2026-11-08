# Nifty 50 TRI weekend-session review register

Date prepared: 2026-11-08  
Experiment: `NIFTY50_PILOT_001`  
Branch: `main`

The acquired TRI has seven weekend-dated observations. A weekend date is not automatically invalid: NSE has held special live equity sessions, including Muhurat sessions and infrastructure/DR exercises. The register at `data/reference/nifty50_tri_weekend_session_review.csv` maps each weekend observation to the relevant exchange circular reference.

## Review outcome

- Seven of seven weekend dates have a specific NSE circular reference and URL recorded for follow-up.
- The January 20, 2024 session is recorded as the regular equity session ultimately conducted that day; the earlier proposed special DR-site schedule was withdrawn.
- This is a source-discovery/reconciliation aid, **not** independent authentication of the acquired TRI values or proof that every row is a valid Nifty 50 TRI observation.
- Original circular bytes still need to be archived and hashed; the circular references need independent review.
- The 2018-01-01 first observation is not a weekend anomaly: contemporaneous market reporting confirms that NSE traded on that Monday. The TRI date/value still requires source-series review.

## Explicit remaining limits

The register does not certify full calendar completeness for 2018-2024, resolve weekday gaps, establish the exact report export semantics, or authenticate the reverse-engineered endpoint response. Do not reject or alter any observation based solely on this register. Research remains HOLD; the holdout remains locked.
