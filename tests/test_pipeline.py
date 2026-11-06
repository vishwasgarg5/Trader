import numpy as np
import pandas as pd
import pytest

from trader.pipeline import rsi, load_universe, validate_universe_prices


def test_rsi_is_bounded():
    close = pd.Series(np.linspace(100, 150, 40))
    values = rsi(close).dropna()
    assert not values.empty
    assert ((values >= 0) & (values <= 100)).all()


def test_universe_contains_nse_symbols():
    symbols = load_universe()
    assert symbols
    assert all(symbol.endswith(".NS") for symbol in symbols)
    assert len(symbols) == len(set(symbols))


def test_configured_universe_is_exactly_49_symbols():
    symbols = load_universe()
    assert len(symbols) == 49
    assert len(symbols) == len(set(symbols))


def test_missing_configured_symbol_fails_closed():
    with pytest.raises(RuntimeError, match="MISSING.NS"):
        validate_universe_prices(["AAA.NS", "MISSING.NS"], {"AAA.NS": pd.DataFrame()})


def test_complete_configured_symbol_set_passes_validation():
    frame = pd.DataFrame({
        "open": np.full(100, 100.0),
        "high": np.full(100, 102.0),
        "low": np.full(100, 99.0),
        "close": np.full(100, 101.0),
        "volume": np.full(100, 1000.0),
    }, index=pd.date_range("2025-01-01", periods=100, freq="B"))
    validate_universe_prices(["AAA.NS"], {"AAA.NS": frame})


def test_empty_configured_price_history_fails_closed():
    with pytest.raises(RuntimeError, match="empty price history"):
        validate_universe_prices(["AAA.NS"], {"AAA.NS": pd.DataFrame()})


def test_short_configured_price_history_fails_closed():
    frame = pd.DataFrame({
        "open": [100.0], "high": [102.0], "low": [99.0],
        "close": [101.0], "volume": [1000.0],
    }, index=pd.to_datetime(["2025-01-01"]))
    with pytest.raises(RuntimeError, match="only 1 valid OHLCV rows"):
        validate_universe_prices(["AAA.NS"], {"AAA.NS": frame})


def test_invalid_configured_ohlcv_fails_closed():
    frame = pd.DataFrame({
        "open": [100.0] * 100, "high": [102.0] * 100,
        "low": [99.0] * 100, "close": [101.0] * 100,
        "volume": [1000.0] * 100,
    }, index=pd.date_range("2025-01-01", periods=100, freq="B"))
    frame.loc[frame.index[0], "close"] = np.inf
    with pytest.raises(RuntimeError, match="only 99 valid OHLCV rows"):
        validate_universe_prices(["AAA.NS"], {"AAA.NS": frame})


def test_signal_generation_is_research_only_when_promotion_gate_is_not_approved():
    from trader.pipeline import FEATURES, make_signals

    class FixedModel:
        def predict_proba(self, frame):
            return np.column_stack([np.zeros(len(frame)), np.full(len(frame), 0.75)])

    date = pd.Timestamp("2026-11-06")
    frame = pd.DataFrame(
        [{**{feature: 0.1 for feature in FEATURES}, "symbol": "AAA.NS",
          "close": 100.0, "atr": 2.0}],
        index=[date],
    )
    signals = make_signals(frame, FixedModel(), promotion_gate={
        "status": "RESEARCH_HOLD",
        "promotion_eligible": False,
        "live_execution_enabled": False,
    })
    assert signals.iloc[0]["model_signal"] == "BUY"
    assert signals.iloc[0]["signal"] == "RESEARCH_ONLY_BUY"
    assert signals.iloc[0]["promotion_status"] == "RESEARCH_HOLD"
    assert signals.iloc[0]["promotion_eligible"] == False


def test_signal_generation_requires_both_approval_and_execution_enablement():
    from trader.pipeline import FEATURES, make_signals

    class FixedModel:
        def predict_proba(self, frame):
            return np.column_stack([np.zeros(len(frame)), np.full(len(frame), 0.75)])

    frame = pd.DataFrame(
        [{**{feature: 0.1 for feature in FEATURES}, "symbol": "AAA.NS",
          "close": 100.0, "atr": 2.0}],
        index=[pd.Timestamp("2026-11-06")],
    )
    signals = make_signals(frame, FixedModel(), promotion_gate={
        "status": "APPROVED",
        "promotion_eligible": True,
        "live_execution_enabled": False,
    })
    assert signals.iloc[0]["signal"] == "RESEARCH_ONLY_BUY"


def test_data_integrity_preflight_persists_missing_symbol_and_evidence_gaps(tmp_path):
    from trader.pipeline import write_data_integrity_report

    report_path = tmp_path / "reports" / "data_integrity.json"
    report = write_data_integrity_report(
        ["AAA.NS", "TATAMOTORS.NS"],
        {"AAA.NS": pd.DataFrame()},
        report_path,
    )
    persisted = __import__("json").loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "BLOCKED_PRICE_DATA"
    assert report["price_validation"]["passed"] is False
    assert "TATAMOTORS.NS" in report["price_validation"]["error"]
    assert persisted["promotion_eligible"] is False
    assert persisted["live_execution_enabled"] is False


def test_configured_price_validation_rejects_duplicate_nse_calendar_dates():
    idx = pd.to_datetime([
        "2025-01-01T18:30:00Z",
        "2025-01-02T04:00:00+05:30",
    ], utc=True)
    frame = pd.DataFrame({
        "open": [100.0, 100.0], "high": [102.0, 102.0],
        "low": [99.0, 99.0], "close": [101.0, 101.0],
        "volume": [1000.0, 1000.0],
    }, index=idx)
    with pytest.raises(RuntimeError, match="duplicate NSE trading dates"):
        validate_universe_prices(["AAA.NS"], {"AAA.NS": frame})
