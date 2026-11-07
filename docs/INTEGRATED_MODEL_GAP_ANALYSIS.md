# Trader integrated event-aware model — architecture and gap analysis

**Reviewed:** 2026-11-07 against current main report and source tree  
**Status:** architecture registered; implementation and data evidence incomplete; RESEARCH HOLD

## Fixed target architecture

Trader will be an event-aware stock research and portfolio system with separate specialist modules feeding one calibrated ranking and portfolio layer. It is not one monolithic classifier. The machine-readable module contract is `config/integrated_model_architecture.json`.

1. Price/technical module: OHLCV, market context, volatility, relative strength and delivery features. Retain the existing five-session research target until a versioned target change is approved.
2. Corporate-action engine: splits, bonus issues, demergers, rights and symbol changes. Its first responsibility is correct price/share-history lineage, not generating a bullish/bearish signal.
3. Dividend module: announcement-timestamped dividend amount, ex-date, record/payment dates and dividend sustainability/total-return context.
4. Buyback module: announcement, method, offer premium, size, record/tender dates, completion and acceptance ratio. An announcement is not treated as a completed offer.
5. News module: timestamped issuer-linked news, event category, sentiment, relevance, novelty and confidence. Preserve first-seen/publication timestamps to prevent look-ahead.
6. IPO/GMP module: a separate listing-event model with issue price, timestamped GMP observations, category-wise subscription, allotment/listing data and realised listing outcomes. GMP is unofficial and must never be presented as guaranteed return.
7. Portfolio engine: holdings, cash, position sizing, concentration, sector exposure, liquidity, transaction costs, drawdown and risk limits.
8. Fusion/calibration layer: combine specialist outputs without double-counting correlated evidence; calibrate probabilities and produce a single ranked research list.
9. Monitoring/reporting: feature coverage, source quality, drift, calibration, net performance and segment diagnostics.

## Current repository report — findings

- Latest saved classification report: 28,567 train rows and 7,252 test rows; test window 2026-03-24 to 2026-10-29; five-session purge; pre-cost accuracy 62.23% versus 63.38% majority baseline; ROC AUC 0.574; Brier score 0.2333. Accuracy is 1.14 percentage points below the majority baseline. This is not evidence of a predictive edge.
- Monitoring report: accuracy 62.08% versus 63.38% majority baseline (fails); PIT membership has zero verified rows; corporate-action lineage has two unresolved rows; drift monitoring has only 2 of 40 required sessions. Research hold is correctly fail-closed.
- Price preflight passes only for the legacy 49-symbol snapshot, 741 rows per configured symbol through 2026-11-05. It does not prove complete NSE history, point-in-time eligibility or inactive/delisted coverage.
- Existing code: technical pipeline, generic timestamped NSE event ingestion, corporate-action audit, delivery/cost-aware experiment, portfolio simulation/diagnostics and monitoring.
- Generic events table currently has headers only (zero rows). The event parser requires announce_date and ex_date but is not a dedicated buyback/dividend research model.
- Corporate-action ledger has two TMPV-related rows with blank adjustment factors; its own audit states price adjustment and dividend total-return treatment remain unverified.
- No dedicated buyback, dividend analytics, news/NLP, IPO/GMP or integrated module-fusion implementation was found in the current source tree.
- Portfolio simulation and diagnostics exist, but portfolio recommendations are not yet driven by the proposed combined event-aware model.
- Latest architecture CI run #38 passed on commit 8077a598cdcfa4c326eca41a8be435e11d5e9bbe. This verifies the protocol documentation/config only, not model performance or data readiness.

## Change inventory

Count: **10 implementation work packages**. Existing components are marked as extensions/revalidation rather than rewritten from scratch.

1. **Security master and data foundation** — effective-dated NSE listing/delisting/suspension, stable IDs, aliases, inactive securities, source timestamps and hashes. This is the first blocker for unbiased broad-universe work.
2. **Corporate-action correction** — independently resolve the two TMPV rows; implement split/bonus/demerger/rights/rename terms, adjusted OHLCV and share-count reconciliation, plus dividend-aware total-return policy.
3. **Dividend module** — typed dividend event schema, reliable NSE/BSE source ingestion, amount/yield/payout features, ex-date treatment and event outcome labels.
4. **Buyback module** — dedicated event schema and lifecycle states; offer premium/size/method, dates, completion and acceptance ratio; avoid announcement/completion leakage.
5. **News module** — source registry, timestamped ingestion, entity resolution, deduplication, event taxonomy, sentiment/relevance/novelty and historical point-in-time replay.
6. **IPO/GMP module** — timestamped GMP history with source-quality labels, subscription/allotment/listing outcomes and separate IPO model evaluation; no mixing IPOs into ordinary-equity history before listing eligibility.
7. **Technical model and staged training** — retain current features as baseline; deterministic representative development sample; chronological purged tuning; freeze model, features, preprocessing, thresholds and hashes before broad evaluation.
8. **Fusion, calibration and output contract** — combine event and technical scores, handle missing modalities explicitly, prevent double counting, calibrate confidence and generate explainable ranked research signals.
9. **Portfolio integration** — connect combined scores to existing portfolio simulator; add event exposure, holdings-aware recommendations, liquidity/capacity, dividend cashflows, split share changes, buyback tender assumptions and net total-return accounting.
10. **Validation, monitoring and paper research** — event-specific and segment evaluation, benchmark/previous-close/logistic baselines, dependence-aware intervals, costs, drift, prospective paper tracking and independent sign-off.

## Recommended implementation order

Do not implement news/GMP scoring before the security identity and timestamped source foundation. Do not use event features in a historical model until event publication timestamps and historical coverage are defensible. Build in this order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10.

## Acceptance and safety

Each module needs schema validation, source provenance, point-in-time replay tests, missing-data behavior, event-specific outcome evaluation and feature ablation against the existing baseline. Compare on identical dates/universe and after costs. The broad evaluation must use frozen inference, not retraining on broad-test labels. Keep final holdout locked until preregistered prerequisites pass.

Maintain RESEARCH_HOLD, promotion_eligible=false, live_execution_enabled=false and full_universe_experiment_authorized=false. CI success is not evidence of a tradable edge.