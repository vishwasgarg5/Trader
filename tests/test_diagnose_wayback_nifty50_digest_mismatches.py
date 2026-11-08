import base64
import hashlib

from scripts.diagnose_wayback_nifty50_digest_mismatches import decode_digest, digest_matches


def test_digest_decoder_compares_raw_sha1_bytes_not_text_encoding():
    payload = b"stable archived payload"
    expected = base64.b32encode(hashlib.sha1(payload).digest()).decode().rstrip("=")
    assert decode_digest(expected) == hashlib.sha1(payload).digest()
    assert digest_matches(payload, expected)
    assert not digest_matches(payload + b"x", expected)
