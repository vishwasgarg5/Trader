import csv
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_rows(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def test_full_text_scope_exclusions_are_archived_and_remain_human_pending():
    scope = _read_rows(
        ROOT / "data/reference/nifty50_unregistered_candidate_scope_review.csv",
        "notice_id",
    )
    inventory = _read_rows(
        ROOT / "data/reference/nifty50_annual_notice_inventory.csv",
        "notice_id",
    )
    queue = _read_rows(
        ROOT / "data/reference/nifty50_notice_review_queue.csv",
        "notice_id",
    )

    cases = {
        "NSE-ARCHIVE-2018-01-08-7ac7d16b6252": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2018-01-08-7ac7d16b6252.txt",
            "required_text": ("NIFTY 500 Index", "NIFTY MidSmallcap 400 Index", "NIFTY Alpha Low-Volatility 30 Index"),
        },
        "NSE-ARCHIVE-2019-12-18-59730c1fbb54": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-12-18-59730c1fbb54.txt",
            "required_text": ("NIFTY 500", "NIFTY Smallcap 250", "NIFTY MidSmallcap 400"),
        },
        "NSE-ARCHIVE-2019-05-02-042b8cce9ec5": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-05-02-042b8cce9ec5.txt",
            "required_text": ("NIFTY 10 Year SDL Index", "IN3420180124 West Bengal", "There are no inclusion"),
        },
    }

    for notice_id, case in cases.items():
        scope_row = scope[notice_id]
        inventory_row = inventory[notice_id]
        queue_row = queue[notice_id]

        assert scope_row["scope_review_status"] == "AI_SCOPE_EXCLUSION_PENDING_HUMAN_SIGNOFF"
        assert scope_row["review_status"] == "AI_REVIEWED"
        assert scope_row["human_signoff_required"].lower() == "true"

        assert inventory_row["observed_nifty50_effect"] == "NO_FLAGSHIP_NIFTY50_CONSTITUENT_CHANGE"
        assert inventory_row["review_status"] == "SCREENED_NO_NIFTY50_CHANGE"
        assert inventory_row["source_document_path"]
        assert inventory_row["source_sha256"]

        pdf_path = ROOT / inventory_row["source_document_path"]
        pdf_bytes = pdf_path.read_bytes()
        assert pdf_bytes.startswith(b"%PDF-")
        assert hashlib.sha256(pdf_bytes).hexdigest() == inventory_row["source_sha256"]

        extracted = (ROOT / case["text_path"]).read_text(encoding="utf-8")
        for phrase in case["required_text"]:
            assert phrase in extracted
        assert not re.search(r"(?im)^\s*\d+\)\s*NIFTY\s+50\s+Index\b", extracted)

        # AI triage is never human approval: the manual queue and decision fields
        # must remain untouched until an actual reviewer signs off.
        assert queue_row["review_status"] == "PENDING_HUMAN_REVIEW"
        assert not queue_row["reviewer"]
        assert not queue_row["reviewed_at"]
        assert not queue_row["verified_effective_date"]
        assert not queue_row["verified_out_symbols"]
        assert not queue_row["verified_in_symbols"]
