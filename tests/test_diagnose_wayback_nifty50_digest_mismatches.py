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
