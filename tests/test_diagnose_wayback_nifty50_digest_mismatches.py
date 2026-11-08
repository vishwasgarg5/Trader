import base64
import hashlib

from scripts.diagnose_wayback_nifty50_digest_mismatches import decode_digest, digest_matches


def test_digest_decoder_compares_raw_sha1_bytes_not_text_encoding():
    payload = b"stable archived payload"
    expected = base64.b32encode(hashlib.sha1(payload).digest()).decode().rstrip("=")
    assert decode_digest(expected) == hashlib.sha1(payload).digest()
    assert digest_matches(payload, expected)
    assert not digest_matches(payload + b"x", expected)


def test_gzip_encoded_payload_matches_cdx_on_wire_bytes_not_decoded_csv():
    import gzip
    payload = b"historical csv bytes"
    encoded = gzip.compress(payload)
    expected = base64.b32encode(hashlib.sha1(encoded).digest()).decode().rstrip("=")
    assert digest_matches(encoded, expected)
    assert not digest_matches(gzip.decompress(encoded), expected)


def test_diagnostic_retries_exact_capture_and_checks_neighbour_without_mutating_state(monkeypatch):
    import io
    import scripts.diagnose_wayback_nifty50_digest_mismatches as module

    good_payload = b"the exact CDX payload"
    wrong_payload = b"replay body differs"
    expected = base64.b32encode(hashlib.sha1(good_payload).digest()).decode().rstrip("=")
    exact = {"timestamp": "20230522051228", "original": "https://example.com/list.csv",
             "statuscode": "200", "digest": expected, "length": str(len(good_payload)),
             "mimetype": "text/csv", "type": "revisit"}
    neighbour = {**exact, "timestamp": "20230522050000", "type": "response"}

    class FakeResponse:
        def __init__(self, status=200, payload=b"", rows=None, url="https://web.archive.org/"):
            self.status_code = status
            self.headers = {"Content-Encoding": "identity", "Memento-Datetime": "Mon, 22 May 2023 05:12:28 GMT"}
            self.raw = io.BytesIO(payload)
            self.url = url
            self._rows = rows
        def json(self):
            return self._rows
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("HTTP failure")
        def close(self):
            pass

    class FakeSession:
        def __init__(self):
            self.calls = 0
        def get(self, url, **kwargs):
            self.calls += 1
            if "cdx/search" in url:
                return FakeResponse(rows=[
                    ["timestamp", "original", "statuscode", "mimetype", "digest", "length", "type"],
                    [exact["timestamp"], exact["original"], "200", "text/csv", expected,
                     exact["length"], "revisit"],
                    [neighbour["timestamp"], neighbour["original"], "200", "text/csv", expected,
                     neighbour["length"], "response"],
                ])
            payload = wrong_payload if self.calls in (2, 3) else good_payload
            return FakeResponse(payload=payload, url=url)

    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    state = {"completed_snapshots": [{
        "status": "CDX_DIGEST_MISMATCH", "capture_timestamp": exact["timestamp"],
        "original_url": exact["original"], "cdx_digest": expected, "quarter": "2023-Q2",
        "cdx_length": exact["length"], "mimetype": "text/csv",
    }]}
    before = repr(state)
    report = module.diagnose(state, FakeSession(), pause_seconds=0)
    result = report["results"][0]
    assert len(result["attempts"]) == 3
    assert result["attempts"][0]["capture_type"] == "revisit"
    assert result["attempts"][0]["wire_digest_match"] is False
    assert result["attempts"][1]["wire_digest_match"] is False
    assert result["attempts"][2]["wire_digest_match"] is True
    assert result["decision"].startswith("CDX_DIGEST_MATCHED_ON_RAW_REPLAY_BYTES")
    assert repr(state) == before
