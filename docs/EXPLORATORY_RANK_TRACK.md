# Exploratory cross-sectional ranking track

This track is deliberately isolated from the registered pilot and production model.

## Status and limitations

Every report is labelled `EXPLORATORY_UNVERIFIED_DATA`. This track does not repair or certify point-in-time membership, corporate actions, stock total returns, TRI, calendars, source authenticity, or broker-cost assumptions. Its metrics are not verified out-of-sample performance and cannot authorize promotion, paper trading, or live trading.

The runner does not download data, read the production model, or open the final holdout. It requires a development-only CSV and an explicit JSON manifest that sets:

- `status`: `EXPLORATORY_UNVERIFIED_DATA`
- `dataset_scope`: `development_only`
- `holdout_included`: `false`
- `production_data_authorized`: `false`

## Input panel schema

Required columns:

- `signal_date`: date after the session close when the signal is formed
- `symbol`: security symbol
- `feature_available_at`: latest availability timestamp for the row's features; must be no later than signal_date
- `outcome_end_date`: date the realised outcome window ends; must be after signal_date
- `net_return`: realised outcome return after the declared exploratory cost assumptions

The registered feature columns are in `config/exploratory_rank_experiment.json`. The first comparison uses within-date percentile-ranked technical and relative-strength features, regularised logistic regression, regularised gradient boosting, an equal-weight rank blend, and a five-session previous-close momentum baseline.

## Run

Create the panel and manifest separately, then run:

```bash
python -m trader.exploratory_rank_experiment \
  --input data/experimental/development_panel.csv \
  --manifest data/experimental/development_manifest.json \
  --output data/experimental/reports/rank_experiment.json \
  --features ret_1,ret_3,ret_5,ret_10,ret_20,sma_5_gap,sma_20_gap,sma_50_gap,rsi_14,macd_gap,bb_position,atr_pct,volume_ratio,relative_ret_5,relative_ret_10,relative_ret_20,relative_strength_rank_5
```

Default evaluation is 3-year training windows and 3-month chronological test windows. Rows whose outcome window has not ended before a test fold are purged. Each qualifying date needs at least 30 securities; exactly five highest-scored securities are evaluated.

## Next stages

Only after the ranking baseline is reproducible should feature enrichment, calibration/abstention and further ensemble work be added. Any new feature needs a point-in-time availability timestamp and a separate ablation report. The holdout remains sealed.
