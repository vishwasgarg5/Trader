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
