import json
from pathlib import Path

import pytest

from scripts.discover_amc_archive_only import validate_discovery_record


FIXTURE = Path(__file__).parent / "fixtures" / "amc_archive_discovery_sample.json"


def _record():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_saved_discovery_fixture_matches_offline_contract():
    record = _record()
    validate_discovery_record(record)
    assert record["counts_as_acquisition_attempt"] is False
    assert record["acquisition_attempts_consumed"] == 0
    assert record["downloads_permitted"] is False
    assert record["download_events_cancelled"] == []


def test_validator_rejects_record_that_claims_downloads_are_permitted():
    record = _record()
    record["downloads_permitted"] = True
    with pytest.raises(ValueError, match="Downloads must remain disabled"):
        validate_discovery_record(record)


def test_validator_rejects_captured_response_bodies():
    record = _record()
    record["responses"][0]["body"] = "<html>not allowed</html>"
    with pytest.raises(ValueError, match="Response bodies must not be captured"):
        validate_discovery_record(record)


def test_validator_rejects_acquisition_attempt_counting():
    record = _record()
    record["counts_as_acquisition_attempt"] = True
    with pytest.raises(ValueError, match="must not count"):
        validate_discovery_record(record)
