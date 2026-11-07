import csv
import hashlib
import io
import zipfile

from trader.nse_archive_access_probe import (
    bhavcopy_url, probe_bhavcopy, probe_pdf,
)


def _zip_bytes():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "bhavcopy.csv",
            "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE\nABC,EQ,1,2,1,2\n",
        )
    return output.getvalue()


def test_legacy_url_uses_uppercase_three_letter_month():
    assert bhavcopy_url("2018-01-02", "legacy").endswith(
        "/2018/JAN/cm02JAN2018bhav.csv.zip"
    )


def test_udiff_url_uses_compact_iso_date():
    assert bhavcopy_url("2024-07-08", "udiff").endswith(
        "BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip"
    )


def test_unknown_format_is_rejected():
    try:
        bhavcopy_url("2024-07-08", "unknown")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("unsupported format accepted")


def test_bhavcopy_probe_checks_zip_crc_and_csv_header():
    payload = _zip_bytes()
    result = probe_bhavcopy(
        "fixture", "2018-01-02", "legacy",
        getter=lambda url: (payload, 200, "application/zip"),
    )
    assert result.status == "PUBLIC_DOWNLOAD_AND_ZIP_VALID"
    assert result.csv_member == "bhavcopy.csv"
    assert result.csv_header[:3] == ["SYMBOL", "SERIES", "OPEN"]
    assert result.sha256 == hashlib.sha256(payload).hexdigest()


def test_bhavcopy_probe_rejects_html_even_if_http_200():
    result = probe_bhavcopy(
        "fixture", "2018-01-02", "legacy",
        getter=lambda url: (b"<html>blocked</html>", 200, "text/html"),
    )
    assert result.status == "FAILED"


def test_pdf_probe_requires_pdf_magic_bytes():
    good = probe_pdf(
        "pdf", "https://example.test/a.pdf",
        getter=lambda url: (b"%PDF-1.7\nfixture", 200, "application/pdf"),
    )
    bad = probe_pdf(
        "html", "https://example.test/b.pdf",
        getter=lambda url: (b"<html>login</html>", 200, "text/html"),
    )
    assert good.status == "PUBLIC_PDF_DOWNLOAD"
    assert bad.status == "FAILED"
