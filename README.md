# Trader — Indian Equity Swing Signal Platform

An open-source GitHub Actions-powered research and paper-signal system for Indian equities. It collects daily prices, builds technical features, trains a five-session upside classifier, ranks candidates, and publishes risk-aware paper signals.

> **RESEARCH HOLD.** The daily model is not promotion-approved. Its probability-ranked outputs are labelled `RESEARCH_ONLY_BUY/HOLD/AVOID`; they are not trade instructions. Live execution remains disabled. This is research software, not investment advice.

## Initial release
- Daily OHLCV collection from Yahoo Finance via yfinance (NSE tickers use `.NS`).
- Technical features, including returns, moving averages, RSI, MACD, Bollinger position, ATR, volume and Nifty context.
- Chronological holdout with a five-session purge to reduce overlapping-label leakage.
- HistGradientBoosting classifier with holdout accuracy, precision, Brier score and ROC AUC.
- Top-five probability ranking, ATR stop/target and conservative risk-based sizing.
- Dated prediction log for later outcome verification.
- Scheduled GitHub Actions workflow with manual dispatch.

## Run locally
Python 3.11 is recommended.

```bash
pip install -r requirements.txt
python -m trader.pipeline
```

Edit `config/universe.txt` to change the Yahoo Finance tickers. The starter list is a configurable Nifty 50-style universe, not a live constituent feed; verify constituents before relying on it.

## Promotion gate

Daily signals are fail-closed by `config/promotion_gate.json`. A raw classifier label is retained in `model_signal`, while the public `signal` field is prefixed with `RESEARCH_ONLY_` unless the gate is explicitly approved, promotion eligibility is true, and live execution is separately enabled. The committed gate is `RESEARCH_HOLD`; CI success alone cannot change it. Do not enable promotion or live execution based on the current research metrics.

## Outputs
- `data/signals/latest_signals.csv`
- `data/logs/predictions.csv`
- `data/reports/metrics.json`
- `models/current_model.joblib`

## Limitations and safeguards
Yahoo Finance is unofficial and may have coverage, corporate-action or timestamp issues. Verify prices against NSE. Holdout metrics are research diagnostics, not evidence of profitability. The initial release does not include options flow, FII/DII, news sentiment, live constituent refresh, transaction-cost-aware paper trading, drift monitoring or guarded challenger promotion. Costs, taxes, slippage, liquidity and survivorship bias must be modelled before evaluating profitability.

## Roadmap
1. Validate data integrity and baseline out-of-sample performance.
2. Add a verified dynamic Nifty 50/200 universe.
3. Add paper trading with costs, portfolio constraints, drawdown and Sharpe metrics.
4. Add regime detection, PSI drift monitoring and evidence-based challenger promotion.
5. Add ensembles, meta-labeling, multiple horizons, Optuna and SHAP.
6. Add dashboard and optional Telegram alerts.

The workflow runs weekdays at 10:20 UTC (15:50 IST), with manual dispatch. GitHub Actions has repository Contents write permission to commit generated files.