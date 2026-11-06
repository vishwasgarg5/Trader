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
