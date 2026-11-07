import hashlib

import pandas as pd
import pytest

from trader.events import EVENT_COLUMNS, merge_events, normalize_nse_actions, yfinance_action_crosscheck


def _source(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def test_nse_loader_preserves_announcement_date_and_hash(tmp_path):
    source = tmp_path / "nse.csv"
    _source(source, [{
        "SYMBOL": "TMPV", "PURPOSE": "INTERIM DIVIDEND",
        "ANNOUNCEMENT DATE": "2025-10-01", "EX-DATE": "2025-10-14",
        "VALUE": "5.00",
    }])
    result = normalize_nse_actions(source, "https://www.nseindia.com/example.csv")
    assert list(result.columns) == EVENT_COLUMNS
    assert result.iloc[0]["symbol"] == "TMPV"
    assert result.iloc[0]["announce_date"] == "2025-10-01"
    assert result.iloc[0]["ex_date"] == "2025-10-14"
    assert result.iloc[0]["source_hash"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_loader_rejects_missing_announcement_date_instead_of_using_ex_date(tmp_path):
    source = tmp_path / "nse.csv"
    _source(source, [{
        "SYMBOL": "TMPV", "PURPOSE": "DIVIDEND",
        "EX-DATE": "2025-10-14", "VALUE": "5.00",
    }])
    with pytest.raises(ValueError, match="missing required fields: announce_date"):
        normalize_nse_actions(source, "https://www.nseindia.com/example.csv")


def test_loader_rejects_announcement_after_ex_date(tmp_path):
    source = tmp_path / "nse.csv"
    _source(source, [{
        "SYMBOL": "TMPV", "PURPOSE": "DIVIDEND",
        "ANNOUNCEMENT DATE": "2025-10-15", "EX-DATE": "2025-10-14",
        "VALUE": "5.00",
    }])
    with pytest.raises(ValueError, match="after ex-date"):
        normalize_nse_actions(source, "https://www.nseindia.com/example.csv")


def test_merge_events_is_idempotent(tmp_path):
    source = tmp_path / "nse.csv"
    _source(source, [{
        "SYMBOL": "TMPV", "PURPOSE": "DIVIDEND",
        "ANNOUNCEMENT DATE": "2025-10-01", "EX-DATE": "2025-10-14",
        "VALUE": "5.00",
    }])
    events = normalize_nse_actions(source, "https://www.nseindia.com/example.csv")
    target = tmp_path / "events.csv"
    assert len(merge_events(events, target)) == 1
    assert len(merge_events(events, target)) == 1
    assert list(pd.read_csv(target).columns) == EVENT_COLUMNS


def test_yfinance_actions_are_reconciliation_only_and_keep_action_date():
    actions = pd.DataFrame(
        {"Dividends": [5.0], "Stock Splits": [0.0]},
        index=pd.to_datetime(["2025-10-14"]),
    )
    result = yfinance_action_crosscheck(actions)
    assert result.iloc[0]["action_date"] == pd.Timestamp("2025-10-14")
    assert result.iloc[0]["dividends"] == 5.0
    assert "announce_date" not in result.columns
