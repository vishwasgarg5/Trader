from datetime import date

from trader.nifty_notice_discovery import discover_entries


def test_discovers_review_candidate_and_keeps_scope():
    html = """
    <div>Aug 23, 2023</div>
    <a href="/Press_Release/ind_prs23082023.pdf">Replacements in indices w.e.f. August 31, 2023</a>
    <div>Sep 25, 2024</div>
    <a href="https://www.niftyindices.com/Press_Release/ind_prs25092024.pdf">Changes in Nifty Fixed Income indices</a>
    <div>Jan 03, 2025</div>
    <a href="/Press_Release/ind_prs03012025.pdf">Replacement in indices</a>
    """
    entries, unparsed = discover_entries(html, 2018, 2024)
    assert len(entries) == 2
    assert entries[0]["date"] == date(2023, 8, 23)
    assert entries[0]["review_candidate"] is True
    assert entries[1]["date"] == date(2024, 9, 25)
    assert unparsed == []


def test_deduplicates_same_pdf_url():
    html = """
    <div>Feb 17, 2023</div>
    <a href="/Press_Release/replacements.pdf">Replacements in indices</a>
    <div>Feb 17, 2023</div>
    <a href="https://www.niftyindices.com/Press_Release/replacements.pdf">Replacements in indices (duplicate link)</a>
    """
    entries, _ = discover_entries(html)
    assert len(entries) == 1


def test_ignores_unrelated_press_release_titles():
    html = """
    <div>Feb 15, 2023</div>
    <a href="/Press_Release/new_index_launch.pdf">NSE Indices launches a new index</a>
    """
    entries, _ = discover_entries(html)
    assert len(entries) == 1
    assert entries[0]["review_candidate"] is False

def test_extracts_relative_pdf_url_from_onclick_handler():
    html = """
    <div>May 18, 2023</div>
    <a onclick="window.open('/Press_Release/multi_asset_review.pdf')">Revision in Nifty Multi Asset Indices</a>
    """
    entries, _ = discover_entries(html)
    assert len(entries) == 1
    assert entries[0]["url"].endswith("/Press_Release/multi_asset_review.pdf")


def test_run_discovery_catalogues_all_archive_entries(monkeypatch, tmp_path):
    from trader import nifty_notice_discovery as discovery
    import csv
    import json

    html = """
    <div>Feb 15, 2023</div>
    <a href="/Press_Release/new_index_launch.pdf">NSE Indices launches a new index</a>
    <div>Aug 23, 2023</div>
    <a href="/Press_Release/replacements.pdf">Replacements in Nifty indices</a>
    """
    monkeypatch.setattr(discovery, "_request", lambda url, max_bytes=30_000_000: html.encode())
    inventory = tmp_path / "nifty50_annual_notice_inventory.csv"
    report_path = tmp_path / "report.json"
    discovery.run_discovery(
        inventory_path=inventory,
        source_dir=tmp_path / "sources",
        report_path=report_path,
        start_year=2023,
        end_year=2023,
        archive_candidates=False,
    )
    catalog_path = tmp_path / "nifty50_archive_discovery_catalog.csv"
    with catalog_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["review_candidate"] for row in rows} == {"true", "false"}
    assert all(row["scope_status"] == "UNREVIEWED" for row in rows)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["archive_catalog_rows_total"] == 2
    assert report["non_candidate_entries_catalogued"] == 1



def test_flags_generic_change_in_indices_as_review_candidate():
    html = """
    <div>Feb 21, 2018</div>
    <a href="/Press_Release/ind_prs21022018.pdf">Change in Indices w.e.f. April 02, 2018</a>
    """
    entries, _ = discover_entries(html, 2018, 2018)
    assert len(entries) == 1
    assert entries[0]["review_candidate"] is True
