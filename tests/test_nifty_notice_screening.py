from trader.nifty_notice_screening import _snippets


def test_text_screening_finds_nifty50_references_and_context():
    snippets = _snippets("The index review covers NIFTY 50. Other text. Nifty50 constituent changes follow.")
    assert len(snippets) == 1  # overlapping context is intentionally deduplicated
    assert "NIFTY 50" in snippets[0]
    assert "Nifty50" in snippets[0]


def test_text_screening_does_not_treat_similar_index_names_as_nifty50():
    assert _snippets("Nifty Next 50 and Nifty 100 are different indices.") == []



def test_screen_pdf_persists_hash_checked_extracted_text(monkeypatch, tmp_path):
    import hashlib
    from trader import nifty_notice_screening as screening

    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    expected_pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    class FakePage:
        def extract_text(self):
            return "NIFTY 50 constituent review"

    class FakeReader:
        pages = [FakePage()]

    monkeypatch.setattr(screening, "PdfReader", lambda *args, **kwargs: FakeReader())
    output_path = tmp_path / "extracted" / "notice.txt"
    result = screening.screen_pdf(pdf_path, expected_pdf_hash, output_path)

    expected_text = "NIFTY 50 constituent review\\n"
    assert output_path.read_text(encoding="utf-8") == expected_text
    assert result["extracted_text_path"] == output_path.as_posix()
    assert result["extracted_text_sha256"] == hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    assert result["text_status"] == "EXTRACTED_NIFTY50_REFERENCE"
