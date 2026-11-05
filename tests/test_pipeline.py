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
    validate_universe_prices(["AAA.NS"], {"AAA.NS": pd.DataFrame()})
