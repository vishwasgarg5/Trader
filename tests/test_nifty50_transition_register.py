import csv
from pathlib import Path


def test_transition_register_uses_superseding_2020_effective_date_and_official_ltim_symbol():
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "reference" / "nifty50_transition_register.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert len(reader.fieldnames or []) == 16
        rows = list(reader)

    by_id = {row["transition_id"]: row for row in rows}
    assert by_id["N50-2020-YESBANK-OUT"]["effective_date"] == "2020-03-19"
    assert by_id["N50-2020-SHREECEM-IN"]["effective_date"] == "2020-03-19"
    assert by_id["N50-2023-LTIM-IN"]["symbol"] == "LTIM"
    assert by_id["N50-2024-LTIM-OUT"]["symbol"] == "LTIM"

    # Register rows are candidate evidence only; this test must not promote them.
    assert all(row["verification_status"] == "SAMPLE_ONLY" for row in rows)


def test_transition_register_has_exactly_sixteen_fields_per_row():
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "reference" / "nifty50_transition_register.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        assert len(header) == 16
        assert all(len(row) == 16 for row in reader)
