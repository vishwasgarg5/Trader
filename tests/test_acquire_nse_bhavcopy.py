import io
import zipfile

import pytest

from scripts.acquire_nse_bhavcopy import bhavcopy_url, parse_bhavcopy_zip


def _zip(csv_text: str) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("sample.csv", csv_text)
    return stream.getvalue()


def test_bhavcopy_url_switches_to_udiff_on_2024_07_08():
    assert "/2018/JAN/cm02JAN2018bhav.csv.zip" in bhavcopy_url("2018-01-02")
    assert "20240708_F_0000.csv.zip" in bhavcopy_url("2024-07-08")


def test_parse_legacy_bhavcopy_keeps_ohlcv_and_isin():
    payload = _zip(
        "SYMBOL,SERIES,DATE1,OPEN,HIGH,LOW,CLOSE,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,ISIN\n"
        "ABC,EQ,02-JAN-2018,10,12,9,11,10,1000,11000,INE123456789\n"
        "ABC,BE,02-JAN-2018,10,12,9,11,10,1000,11000,INE123456789\n"
    )
    member, rows = parse_bhavcopy_zip(payload, "2018-01-02")
    assert member == "sample.csv"
    assert rows == [{
        "trade_date": "2018-01-02", "symbol": "ABC", "series": "EQ",
        "isin": "INE123456789", "open": 10.0, "high": 12.0, "low": 9.0,
        "close": 11.0, "previous_close": 10.0, "volume": 1000.0, "turnover": 11000.0,
    }]


def test_parse_udiff_bhavcopy_schema():
    payload = _zip(
        "TradDt,TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal,ISIN\n"
        "2024-07-08,ABC,EQ,10,12,9,11,10,1000,11000,INE123456789\n"
    )
    _, rows = parse_bhavcopy_zip(payload, "2024-07-08")
    assert rows[0]["isin"] == "INE123456789"
    assert rows[0]["turnover"] == 11000.0


def test_parser_rejects_wrong_date_and_bad_isin():
    wrong_date = _zip(
        "SYMBOL,SERIES,DATE1,OPEN,HIGH,LOW,CLOSE,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,ISIN\n"
        "ABC,EQ,03-JAN-2018,10,12,9,11,10,1000,11000,INE123456789\n"
    )
    with pytest.raises(ValueError, match="date mismatch"):
        parse_bhavcopy_zip(wrong_date, "2018-01-02")
    bad_isin = _zip(
        "SYMBOL,SERIES,DATE1,OPEN,HIGH,LOW,CLOSE,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,ISIN\n"
        "ABC,EQ,02-JAN-2018,10,12,9,11,10,1000,11000,BAD\n"
    )
    with pytest.raises(ValueError, match="invalid/missing ISIN"):
        parse_bhavcopy_zip(bad_isin, "2018-01-02")


def test_calendar_manifest_requires_human_review_unless_candidate_flag(tmp_path):
    import csv
    import hashlib
    from scripts.acquire_nse_bhavcopy import load_calendar_manifest
    source = tmp_path / "source.json"
    source.write_text('{"source":"official"}', encoding="utf-8")
    manifest = tmp_path / "calendar.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "trade_date", "calendar_source_url", "calendar_source_path",
            "calendar_source_sha256", "calendar_review_status",
        ])
        writer.writeheader()
        writer.writerow({
            "trade_date": "2018-01-02", "calendar_source_url": "https://example.com/calendar",
            "calendar_source_path": "source.json",
            "calendar_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "calendar_review_status": "CANDIDATE_UNREVIEWED",
        })
    # This unit test relocates the module root so the manifest source path is checked locally.
    import scripts.acquire_nse_bhavcopy as module
    original_root = module.ROOT
    module.ROOT = tmp_path
    try:
        with pytest.raises(ValueError, match="not human-reviewed"):
            load_calendar_manifest(manifest)
        assert len(load_calendar_manifest(manifest, allow_candidate_calendar=True)) == 1
    finally:
        module.ROOT = original_root
