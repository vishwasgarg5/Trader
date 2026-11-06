from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yfinance as yf

from trader.corporate_actions import audit_corporate_action_ledger
from trader.universe_audit import audit_universe
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, roc_auc_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MODELS = ROOT / "models"
LOG = logging.getLogger("trader")

FEATURES = [
    "ret_1", "ret_3", "ret_5", "ret_10", "ret_20",
    "sma_5_gap", "sma_20_gap", "sma_50_gap", "rsi_14",
    "macd_gap", "bb_position", "atr_pct", "volume_ratio",
    "nifty_ret_1", "nifty_ret_5", "nifty_vix",
]
HORIZON = 5
TARGET_RETURN = 0.01
RISK_FRACTION = 0.005
MAX_POSITION_FRACTION = 0.10


def load_universe(path: Path = ROOT / "config" / "universe.txt") -> list[str]:
    return [
        line.strip() for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def download_prices(tickers: list[str], period: str = "3y") -> dict[str, pd.DataFrame]:
    symbols = list(dict.fromkeys([*tickers, "^NSEI", "^INDIAVIX"]))
    raw = yf.download(
        symbols, period=period, interval="1d", auto_adjust=True,
        group_by="ticker", progress=False, threads=True,
    )
    if raw.empty:
        raise RuntimeError("Yahoo Finance returned no price data")
    result: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                frame = raw[symbol].copy()
            elif len(symbols) == 1:
                frame = raw.copy()
            else:
                continue
            frame.columns = [str(c).lower() for c in frame.columns]
            required = ["open", "high", "low", "close", "volume"]
            if not set(required).issubset(frame.columns):
                continue
            frame = frame[required].apply(pd.to_numeric, errors="coerce")
            frame = frame.dropna(subset=required).sort_index()
            frame = frame.loc[np.isfinite(frame[required]).all(axis=1)]
            frame = frame.loc[
                (frame[["open", "high", "low", "close"]] > 0).all(axis=1)
                & (frame["volume"] >= 0)
                & (frame["high"] >= frame[["open", "low", "close"]].max(axis=1))
                & (frame["low"] <= frame[["open", "high", "close"]].min(axis=1))
            ]
            idx = pd.to_datetime(frame.index)
            if idx.tz is not None:
                idx = idx.tz_localize(None)
            frame.index = idx
            if frame.index.has_duplicates:
                raise ValueError("duplicate trading dates")
            result[symbol] = frame
        except (KeyError, TypeError, ValueError):
            LOG.warning("No usable data for %s", symbol)
    return result


def validate_universe_prices(
    tickers: list[str], prices: dict[str, pd.DataFrame], *, minimum_rows: int = 100,
) -> None:
    """Require usable history for every configured symbol before feature generation."""
    if len(tickers) != len(set(tickers)):
        raise RuntimeError("Configured universe contains duplicate symbols")
    missing = sorted(set(tickers).difference(prices))
    if missing:
        raise RuntimeError(
            "Missing price history for configured universe symbols: " + ", ".join(missing)
        )

    required = ["open", "high", "low", "close", "volume"]
    invalid: list[str] = []
    for symbol in tickers:
        frame = prices[symbol]
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            invalid.append(f"{symbol} (empty price history)")
            continue
        if not set(required).issubset(frame.columns):
            invalid.append(f"{symbol} (missing OHLCV columns)")
            continue
        values = frame[required].apply(pd.to_numeric, errors="coerce")
        valid = (
            np.isfinite(values).all(axis=1)
            & (values[["open", "high", "low", "close"]] > 0).all(axis=1)
            & (values["volume"] >= 0)
            & (values["high"] >= values[["open", "low", "close"]].max(axis=1))
            & (values["low"] <= values[["open", "high", "close"]].min(axis=1))
        )
        dates = pd.to_datetime(frame.index, errors="coerce")
        if dates.isna().any():
            invalid.append(f"{symbol} (invalid trading dates)")
        elif getattr(dates, "tz", None) is not None:
            dates = dates.tz_convert("Asia/Kolkata").tz_localize(None).normalize()
            if dates.has_duplicates:
                invalid.append(f"{symbol} (duplicate NSE trading dates)")
            elif not dates.is_monotonic_increasing:
                invalid.append(f"{symbol} (trading dates are not increasing)")
            elif int(valid.sum()) < minimum_rows:
                invalid.append(
                    f"{symbol} (only {int(valid.sum())} valid OHLCV rows; need {minimum_rows})"
                )
        elif dates.normalize().has_duplicates:
            invalid.append(f"{symbol} (duplicate NSE trading dates)")
        elif not dates.is_monotonic_increasing:
            invalid.append(f"{symbol} (trading dates are not increasing)")
        elif int(valid.sum()) < minimum_rows:
            invalid.append(
                f"{symbol} (only {int(valid.sum())} valid OHLCV rows; need {minimum_rows})"
            )
    if invalid:
        raise RuntimeError("Unusable configured price history: " + "; ".join(invalid))


def write_data_integrity_report(
    tickers: list[str],
    prices: dict[str, pd.DataFrame],
    output_path: Path | None = None,
) -> dict:
    """Persist a preflight audit before the daily pipeline can fail closed."""
    output_path = output_path or DATA / "reports" / "data_integrity.json"
    membership_path = DATA / "reference" / "universe_membership.csv"
    corporate_action_path = DATA / "reference" / "corporate_actions.csv"
    universe_report = audit_universe(prices, tickers, membership_path)
    corporate_action_report = audit_corporate_action_ledger(corporate_action_path)
    validation_error = None
    try:
        validate_universe_prices(tickers, prices)
    except RuntimeError as exc:
        validation_error = str(exc)

    evidence_gaps = []
    if not universe_report.get("membership_history", {}).get("valid"):
        evidence_gaps.append("Historical membership evidence is absent or invalid.")
    if not corporate_action_report.get("corporate_action_adjustment_verified", False):
        evidence_gaps.append("Corporate-action adjusted-price lineage is not independently verified.")
    report = {
        "schema_version": 1,
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "configured_symbols": list(tickers),
        "configured_symbol_count": len(tickers),
        "price_validation": {
            "passed": validation_error is None,
            "minimum_valid_rows_per_symbol": 100,
            "error": validation_error,
        },
        "universe_audit": universe_report,
        "corporate_action_audit": corporate_action_report,
        "research_evidence_gaps": evidence_gaps,
        "status": (
            "BLOCKED_PRICE_DATA" if validation_error
            else "RESEARCH_ONLY_EVIDENCE_GAPS" if evidence_gaps
            else "PRICE_DATA_VALID_REQUIRES_INDEPENDENT_REVIEW"
        ),
        "promotion_eligible": False,
        "live_execution_enabled": False,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    values = 100 - 100 / (1 + rs)
    values = values.mask((loss == 0) & (gain > 0), 100)
    values = values.mask((gain == 0) & (loss > 0), 0)
    return values


def build_features(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if "^NSEI" not in prices:
        raise RuntimeError("Nifty 50 (^NSEI) context data is required")
    nifty = prices["^NSEI"]["close"]
    vix = prices.get("^INDIAVIX", pd.DataFrame()).get("close", pd.Series(dtype=float))
    rows = []
    for symbol, frame in prices.items():
        if symbol.startswith("^") or len(frame) < 100:
            continue
        close, high, low, volume = frame["close"], frame["high"], frame["low"], frame["volume"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        mid, std = close.rolling(20).mean(), close.rolling(20).std()
        f = pd.DataFrame(index=frame.index)
        for n in (1, 3, 5, 10, 20):
            f[f"ret_{n}"] = close.pct_change(n)
        f["sma_5_gap"] = close / close.rolling(5).mean() - 1
        f["sma_20_gap"] = close / close.rolling(20).mean() - 1
        f["sma_50_gap"] = close / close.rolling(50).mean() - 1
        f["rsi_14"] = rsi(close)
        f["macd_gap"] = (ema12 - ema26) / close
        f["bb_position"] = (close - mid) / (2 * std)
        f["atr_pct"] = atr / close
        f["volume_ratio"] = volume / volume.rolling(20).mean()
        f["nifty_ret_1"] = nifty.pct_change(1).reindex(f.index)
        f["nifty_ret_5"] = nifty.pct_change(5).reindex(f.index)
        f["nifty_vix"] = vix.reindex(f.index).ffill()
        f["symbol"] = symbol
        f["close"] = close
        f["atr"] = atr
        f["future_return"] = close.shift(-HORIZON) / close - 1
        f["target"] = (f["future_return"] > TARGET_RETURN).astype(float)
        f.loc[f.index[-HORIZON:], "target"] = np.nan
        rows.append(f.replace([np.inf, -np.inf], np.nan))
    if not rows:
        raise RuntimeError("No stock has enough history to build features")
    return pd.concat(rows).sort_index()


def make_model() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("classifier", HistGradientBoostingClassifier(
            max_iter=160, learning_rate=0.06, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=42,
        )),
    ])


def train_and_evaluate(frame: pd.DataFrame) -> tuple[Pipeline, dict]:
    labelled = frame.dropna(subset=["target"]).copy()
    dates = np.array(sorted(labelled.index.unique()))
    if len(dates) < 150:
        raise RuntimeError(f"Insufficient history: only {len(dates)} trading dates")
    split = int(len(dates) * 0.8)
    train_dates = dates[:max(1, split - HORIZON)]
    test_dates = dates[split:]
    train = labelled.loc[labelled.index.isin(train_dates)]
    test = labelled.loc[labelled.index.isin(test_dates)]
    if (train.empty or test.empty or train["target"].nunique() < 2
            or test["target"].nunique() < 2):
        raise RuntimeError("Chronological train/holdout split is too small or contains one target class")
    model = make_model()
    model.fit(train[FEATURES], train["target"].astype(int))
    probabilities = model.predict_proba(test[FEATURES])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_end": str(train.index.max().date()),
        "test_start": str(test.index.min().date()),
        "test_end": str(test.index.max().date()),
        "positive_rate": float(test["target"].mean()),
        "accuracy": float(accuracy_score(test["target"], predictions)),
        "precision_at_0_5": float(precision_score(test["target"], predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(test["target"], probabilities)),
        "roc_auc": float(roc_auc_score(test["target"], probabilities)),
        "baseline_accuracy_majority": float(max(test["target"].mean(), 1 - test["target"].mean())),
        "target_return": TARGET_RETURN,
        "horizon_sessions": HORIZON,
        "validation": "chronological holdout with five-session purge; before costs",
    }
    final_model = make_model()
    final_model.fit(labelled[FEATURES], labelled["target"].astype(int))
    return final_model, metrics


def make_signals(
    frame: pd.DataFrame,
    model: Pipeline,
    promotion_gate: dict | None = None,
) -> pd.DataFrame:
    """Create explicitly research-labelled signals unless promotion is approved."""
    if promotion_gate is None:
        gate_path = ROOT / "config" / "promotion_gate.json"
        try:
            promotion_gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            promotion_gate = {}
    if not isinstance(promotion_gate, dict):
        promotion_gate = {}
    promotion_eligible = (
        promotion_gate.get("status") == "APPROVED"
        and promotion_gate.get("promotion_eligible") is True
        and promotion_gate.get("live_execution_enabled") is True
    )
    latest_date = frame.index.max()
    latest = frame.loc[frame.index == latest_date].dropna(subset=FEATURES).copy()
    if latest.empty:
        raise RuntimeError("No complete latest-day feature rows")
    latest["prob_up_5d"] = model.predict_proba(latest[FEATURES])[:, 1]
    latest = latest.sort_values("prob_up_5d", ascending=False).head(5).copy()
    latest["entry"] = latest["close"]
    latest["stop_loss"] = latest["entry"] - 1.5 * latest["atr"]
    latest["target_price"] = latest["entry"] + 2.0 * latest["atr"]
    latest["risk_per_share"] = latest["entry"] - latest["stop_loss"]
    latest["model_signal"] = np.where(
        latest["prob_up_5d"] >= 0.60, "BUY",
        np.where(latest["prob_up_5d"] <= 0.40, "AVOID", "HOLD"),
    )
    latest["signal"] = (
        latest["model_signal"] if promotion_eligible
        else "RESEARCH_ONLY_" + latest["model_signal"]
    )
    latest["promotion_status"] = "APPROVED" if promotion_eligible else "RESEARCH_HOLD"
    latest["promotion_eligible"] = bool(promotion_eligible)
    latest["position_fraction"] = np.minimum(
        RISK_FRACTION * latest["entry"] / latest["risk_per_share"].replace(0, np.nan),
        MAX_POSITION_FRACTION,
    ).fillna(0)
    latest["as_of"] = latest.index.strftime("%Y-%m-%d")
    return latest.reset_index(drop=True)[[
        "as_of", "symbol", "signal", "model_signal", "promotion_status",
        "promotion_eligible", "prob_up_5d", "entry", "stop_loss",
        "target_price", "atr", "position_fraction",
    ]]


def update_prediction_log(signals: pd.DataFrame) -> None:
    path = DATA / "logs" / "predictions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = pd.read_csv(path)
        combined = pd.concat([old, signals], ignore_index=True)
        combined = combined.drop_duplicates(["as_of", "symbol"], keep="last")
    else:
        combined = signals.copy()
    combined.to_csv(path, index=False)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    DATA.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    universe = load_universe()
    prices = download_prices(universe)
    integrity_report = write_data_integrity_report(universe, prices)
    if not integrity_report["price_validation"]["passed"]:
        raise RuntimeError(integrity_report["price_validation"]["error"])
    frame = build_features(prices)
    model, metrics = train_and_evaluate(frame)
    signals = make_signals(frame, model)
    joblib.dump(
        {"model": model, "features": FEATURES, "metrics": metrics},
        MODELS / "current_model.joblib",
    )
    (DATA / "signals").mkdir(parents=True, exist_ok=True)
    (DATA / "reports").mkdir(parents=True, exist_ok=True)
    signals.to_csv(DATA / "signals" / "latest_signals.csv", index=False)
    (DATA / "reports" / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    update_prediction_log(signals)
    LOG.info("Completed. Holdout metrics: %s", metrics)
    LOG.info("Top candidates: %s", signals[["symbol", "signal", "prob_up_5d"]].to_dict("records"))


if __name__ == "__main__":
    main()
