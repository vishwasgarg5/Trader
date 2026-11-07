from trader.nifty50_index_reconstruction import reconstruct_price_index

DAY = "2024-01-02"
REVIEW = {"source_url": "https://www.niftyindices.com/source.pdf",
          "evidence_sha256": "a" * 64, "reviewer": "reviewer-1", "reviewed_at": "2024-01-03"}


def fixtures(count=50):
    members, inputs = [], []
    for i in range(count):
        sid = f"SEC{i:02d}"
        members.append({"security_id": sid, "symbol": f"S{i:02d}",
                        "valid_from": "2020-01-01", "valid_to": "",
                        "verification_status": "VERIFIED", **REVIEW})
        inputs.append({"security_id": sid, "date": DAY, "close": 100.0,
                       "free_float_shares": 1000.0,
                       "investible_weight_factor": 0.5, **REVIEW})
    return members, inputs, [{"date": DAY, "divisor": 2500.0, **REVIEW}], [
        {"date": DAY, "index_level": 1000.0, **REVIEW}]


def test_exact_synthetic_reconstruction_matches_without_fitting():
    m, x, d, o = fixtures()
    result = reconstruct_price_index([DAY], m, x, d, o, tolerance_points=0.01)
    assert result["status"] == "MATCH"
    assert result["rows"][0]["reconstructed_level"] == 1000.0
    assert result["parameter_fitting"] is False
    assert result["membership_written"] is False
    assert result["tri_reconstructed"] is False


def test_missing_tolerance_fails_closed():
    m, x, d, o = fixtures()
    result = reconstruct_price_index([DAY], m, x, d, o, tolerance_points=None)
    assert result["status"] == "INSUFFICIENT_INPUTS"
    assert "pre-registered" in result["reason"]


def test_wrong_constituent_count_fails_closed():
    m, x, d, o = fixtures(49)
    result = reconstruct_price_index([DAY], m, x, d, o, tolerance_points=0.01)
    assert result["status"] == "INSUFFICIENT_INPUTS"
    assert "exactly 50" in result["rows"][0]["reason"]


def test_missing_security_input_fails_closed():
    m, x, d, o = fixtures()
    x.pop()
    result = reconstruct_price_index([DAY], m, x, d, o, tolerance_points=0.01)
    assert result["status"] == "INSUFFICIENT_INPUTS"
    assert result["rows"][0]["status"] == "INSUFFICIENT_INPUTS"


def test_official_level_outside_tolerance_is_mismatch_not_refitted():
    m, x, d, o = fixtures()
    o[0]["index_level"] = 990.0
    result = reconstruct_price_index([DAY], m, x, d, o, tolerance_points=0.01)
    assert result["status"] == "MISMATCH"
    assert result["rows"][0]["residual_points"] == 10.0
    assert result["parameter_fitting"] is False


def test_missing_divisor_is_not_assumed_or_fitted():
    m, x, d, o = fixtures()
    result = reconstruct_price_index([DAY], m, x, [], o, tolerance_points=0.01)
    assert result["status"] == "INSUFFICIENT_INPUTS"
    assert "divisor" in result["rows"][0]["reason"]


def test_unreviewed_membership_does_not_count():
    m, x, d, o = fixtures()
    m[0]["verification_status"] = "SAMPLE_ONLY"
    result = reconstruct_price_index([DAY], m, x, d, o, tolerance_points=0.01)
    assert result["status"] == "INSUFFICIENT_INPUTS"
