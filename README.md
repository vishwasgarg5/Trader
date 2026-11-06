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
Yahoo Finance is unofficial and may have coverage, corporate-action or timestamp issues. Verify prices against NSE. The research code now includes transaction-cost-aware walk-forward and portfolio diagnostics, but Groww tariff arithmetic still needs actual contract-note reconciliation, price history and corporate-action lineage need independent verification, and point-in-time membership remains unverified. Holdout metrics are research diagnostics, not evidence of profitability. Live execution is disabled.

## Roadmap
1. Complete 49-symbol historical data, corporate-action and point-in-time membership evidence.
2. Reconcile Groww delivery charges against anonymised contract notes and validate execution assumptions.
3. Complete independent walk-forward review and evaluate the locked final holdout only after all preconditions pass.
4. Run prospective paper trading with costs, portfolio constraints, drawdown and drift monitoring.
5. Consider challenger models only after the existing research stopping rules justify further model work.
6. Add dashboard and optional Telegram alerts.

The workflow runs weekdays at 10:20 UTC (15:50 IST), with manual dispatch. GitHub Actions has repository Contents write permission to commit generated files.