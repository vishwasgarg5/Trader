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
