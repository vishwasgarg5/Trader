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
        "NSE-ARCHIVE-2019-05-07-be5ec74deef5": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-05-07-be5ec74deef5.txt",
            "required_text": ("NIFTY 10 Year SDL Index", "IN2020190046 Kerala", "IN2920190039 Rajasthan"),
        },
        "NSE-ARCHIVE-2019-06-24-0977558a6043": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-06-24-0977558a6043.txt",
            "required_text": ("NIFTY 11-15 yr G-Sec Index", "NIFTY Composite G-Sec Index", "IN0020160100", "IN0020190065"),
        },
        "NSE-ARCHIVE-2019-06-25-3e79e53badb5": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-06-25-3e79e53badb5.txt",
            "required_text": ("NIFTY SME EMERGE", "Five Core Electronics Ltd.", "FIVECORE", "No inclusion is being made"),
        },
        "NSE-ARCHIVE-2019-06-25-a8c546e97112": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-06-25-a8c546e97112.txt",
            "required_text": ("NIFTY 10 Year SDL Index", "IN1020180221 Andhra Pradesh", "IN3420190016 West Bengal", "The following securities are being included"),
        },
        "NSE-ARCHIVE-2019-06-13-8b59c9ce840e": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-06-13-8b59c9ce840e.txt",
            "required_text": ("NIFTY 500", "NIFTY Midcap 150", "NIFTY Infrastructure", "NIFTY Alpha 50"),
        },
        "NSE-ARCHIVE-2019-06-18-d3348f86fda0": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-06-18-d3348f86fda0.txt",
            "required_text": ("NIFTY 10 Year SDL Index", "IN1520180325 Gujarat", "IN3420180181 West Bengal", "There are no inclusions"),
        },
        "NSE-ARCHIVE-2019-05-14-cde78c64905a": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-05-14-cde78c64905a.txt",
            "required_text": ("NIFTY 10 Year SDL Index", "IN1320180053 Bihar", "IN2020190053 Kerala", "IN2920190047 Rajasthan"),
        },
        "NSE-ARCHIVE-2019-05-08-9b9dab3479fa": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-05-08-9b9dab3479fa.txt",
            "required_text": ("NIFTY SME EMERGE", "One Point One Solutions Ltd.", "ONEPOINT", "No inclusion is being made"),
        },
        "NSE-ARCHIVE-2019-06-28-b9d3352bec90": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-06-28-b9d3352bec90.txt",
            "required_text": ("NIFTY100 Alpha 30", "30 companies selected from its parent NIFTY 100 index", "quarterly basis"),
        },
        "NSE-ARCHIVE-2019-07-08-cb472e61d83b": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-07-08-cb472e61d83b.txt",
            "required_text": ("NIFTY CPSE", "REC Limited", "RECLTD", "NIFTY SME EMERGE", "INFOBEAN", "SANGINITA", "July 15, 2019"),
        },
        "NSE-ARCHIVE-2019-07-09-c7702a0846f9": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-07-09-c7702a0846f9.txt",
            "required_text": ("NIFTY 10 Year SDL Index", "IN1320180079 Bihar", "IN1320190011 Bihar", "IN2020190103 Kerala", "IN2120190037 Madhya Pradesh"),
        },
        "NSE-ARCHIVE-2019-07-09-ff433ab59d76": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-07-09-ff433ab59d76.txt",
            "required_text": ("NIFTY SME EMERGE", "Sirca Paints India Ltd.", "SIRCA", "No inclusion is being made", "July 16, 2019"),
        },
        "NSE-ARCHIVE-2019-07-02-3d22aa40d54f": {
            "text_path": "data/reference/extracted_notice_text/NSE-ARCHIVE-2019-07-02-3d22aa40d54f.txt",
            "required_text": ("NIFTY 10 Year SDL Index", "IN1520180341 Gujarat", "IN3420180207 West Bengal", "IN1820190057 Jammu and Kashmir", "IN3120190043 Tamil Nadu"),
        },
    }

    for notice_id, case in cases.items():
        scope_row = scope[notice_id]
        inventory_row = inventory[notice_id]
        queue_row = queue[notice_id]

        assert scope_row["scope_review_status"] == "AI_SCOPE_EXCLUSION_PENDING_HUMAN_SIGNOFF"
        assert scope_row["review_status"] == "AI_REVIEWED"
        assert scope_row["human_signoff_required"].lower() == "true"

        # Canonical inventory value for every AI-screened non-NIFTY-50 notice.
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
        assert queue_row["review_status"] == "AI_REVIEWED_PENDING_HUMAN_SIGNOFF"
        assert not queue_row["reviewer"]
        assert not queue_row["reviewed_at"]
        assert not queue_row["verified_effective_date"]
        assert not queue_row["verified_out_symbols"]
        # Screening notes belong only in notes, never in verified symbol fields.
        assert not queue_row["verified_in_symbols"]
