import numpy as np
import pandas as pd

from trader.pipeline import rsi, load_universe


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
