from trader.nifty_notice_screening import _snippets


def test_text_screening_finds_nifty50_references_and_context():
    snippets = _snippets("The index review covers NIFTY 50. Other text. Nifty50 constituent changes follow.")
    assert len(snippets) == 2
    assert "NIFTY 50" in snippets[0]
    assert "Nifty50" in snippets[1]


def test_text_screening_does_not_treat_similar_index_names_as_nifty50():
    assert _snippets("Nifty Next 50 and Nifty 100 are different indices.") == []
