import numpy as np
import pandas as pd

from trader.pipeline import _rsi, load_universe


def test_rsi_is_bounded():
    close = pd.Series(np.linspace(100, 150, 40))
    rsi = _rsi(close).dropna()
    assert not rsi.empty
    assert ((rsi >= 0) & (rsi <= 100)).all()


def test_universe_contains_nse_symbols():
    symbols = load_universe()
    assert symbols
    assert all(symbol.endswith(".NS") for symbol in symbols)
    assert len(symbols) == len(set(symbols))
