import pandas as pd
import pytest

from trader.delivery import parse_full_bhavcopy


def test_parse_full_bhavcopy_filters_eq_symbols_and_reads_delivery_percent():
    csv = (
        "SYMBOL,SERIES,DATE1,DELIV_PER\n"
        "RELIANCE,EQ,05-Nov-2026,42.5\n"
        "RELIANCE,BE,05-Nov-2026,10.0\n"
        "TCS,EQ,05-Nov-2026,55.0\n"
    ).encode()
    result = parse_full_bhavcopy(
        csv, pd.Timestamp("2026-11-05"), {"RELIANCE", "TCS"}
    )
    assert set(result["symbol"]) == {"RELIANCE.NS", "TCS.NS"}
    assert result.loc[result["symbol"] == "RELIANCE.NS", "delivery_pct"].iloc[0] == 42.5


def test_parse_full_bhavcopy_rejects_stale_or_wrong_date():
    csv = (
        "SYMBOL,SERIES,DATE1,DELIV_PER\n"
        "RELIANCE,EQ,04-Nov-2026,42.5\n"
    ).encode()
    with pytest.raises(ValueError, match="date mismatch"):
        parse_full_bhavcopy(csv, pd.Timestamp("2026-11-05"), {"RELIANCE"})



def test_parse_full_bhavcopy_accepts_legacy_windows_encoding():
    # NSE archive responses have occasionally contained Windows-1252 bytes.
    csv = (
        "SYMBOL,SERIES,DATE1,DELIV_PER,NOTES\n"
        "RELIANCE,EQ,05-Nov-2026,42.5,legacy–encoding\n"
    ).encode("cp1252")
    result = parse_full_bhavcopy(
        csv, pd.Timestamp("2026-11-05"), {"RELIANCE"}
    )
    assert result.loc[0, "delivery_pct"] == 42.5
