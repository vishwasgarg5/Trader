import numpy as np
import pandas as pd
import pytest

from trader.nifty50_pilot_controls import (
    build_point_in_time_feature_snapshot,
    build_purged_walk_forward_folds,
    estimate_precision_lift_mde,
    evaluate_all_pilot_gates,
    evaluate_factor_alpha_gate,
    sha256_bytes,
    validate_point_in_time_features,
    validate_source_manifest,
    verify_source_manifest_payloads,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def _features():
    return pd.DataFrame([
        {"security_id":"INE000A01001","feature_name":"sentiment","value":0.2,
         "published_at":"2024-01-02T10:00:00+05:30","first_seen_at":"2024-01-02T10:01:00+05:30",
         "source_url":"https://nseindia.com/a","source_sha256":HASH_A},
        {"security_id":"INE000A01001","feature_name":"sentiment","value":0.8,
         "published_at":"2024-01-04T10:00:00+05:30","first_seen_at":"2024-01-05T10:00:00+05:30",
         "source_url":"https://nseindia.com/b","source_sha256":HASH_B},
    ])


def test_feature_snapshot_uses_first_seen_and_never_future_revision():
    features = _features()
    signals = pd.DataFrame([
        {"signal_id":"S1","security_id":"INE000A01001","signal_timestamp":"2024-01-03T15:30:00+05:30"},
        {"signal_id":"S2","security_id":"INE000A01001","signal_timestamp":"2024-01-06T15:30:00+05:30"},
    ])
    result = build_point_in_time_feature_snapshot(features, signals)
    assert result.groupby("signal_id")["value"].first().to_dict() == {"S1":0.2,"S2":0.8}
    assert (result["available_at"] <= result["signal_timestamp"]).all()


def test_feature_rejects_bad_hash_and_non_https_source():
    bad = _features()
    bad.loc[0, "source_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="SHA-256"):
        validate_point_in_time_features(bad)
    bad = _features()
    bad.loc[0, "source_url"] = "http://nseindia.com/a"
    with pytest.raises(ValueError, match="HTTPS"):
        validate_point_in_time_features(bad)


def test_feature_rejects_duplicate_provenance_rows():
    bad = pd.concat([_features().iloc[[0]], _features().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_point_in_time_features(bad)


def test_source_manifest_validates_hash_url_and_unique_ids():
    manifest = pd.DataFrame([{
        "source_id":"NSE-1","source_url":"https://nseindia.com/a",
        "source_sha256":HASH_A,"retrieved_at":"2024-01-02T10:00:00Z"
    }])
    assert len(validate_source_manifest(manifest)) == 1
    manifest.loc[1 if len(manifest)>1 else 0, "source_sha256"] = "bad"
    with pytest.raises(ValueError, match="SHA-256"):
        validate_source_manifest(manifest)


def test_sha256_is_over_original_bytes():
    assert sha256_bytes(b"original") == "0682c5f2076f099c34cfdd15a9e063849ed437a49677e6fcc5b4198c76575be5"


def test_mde_is_reproducible_and_respects_six_percentage_point_ceiling():
    rows = []
    for i in range(80):
        rows.append({
            "date":pd.Timestamp("2020-01-01")+pd.Timedelta(days=i),
            "selected_positive_count":2 if i%3 else 3,
            "selected_count":5,
            "eligible_positive_count":int(10 + (i%4)),
            "eligible_count":50,
        })
    frame = pd.DataFrame(rows)
    a = estimate_precision_lift_mde(frame, alpha=0.05, target_power=0.8, seed=17,
                                    simulations=1000, block_sessions=20)
    b = estimate_precision_lift_mde(frame, alpha=0.05, target_power=0.8, seed=17,
                                    simulations=1000, block_sessions=20)
    assert a == b
    assert a["seed"] == 17
    assert a["block_sessions"] == 20
    assert a["decision"] in {"MDE_WITHIN_REGISTERED_CEILING","INCONCLUSIVE"}


def test_mde_rejects_wrong_selection_count_and_short_history_is_inconclusive():
    short = pd.DataFrame([{
        "date":"2020-01-01","selected_positive_count":1,"selected_count":4,
        "eligible_positive_count":10,"eligible_count":50
    }])
    with pytest.raises(ValueError, match="exactly five"):
        estimate_precision_lift_mde(short, alpha=0.05, target_power=0.8, seed=1)
    short.loc[0,"selected_count"] = 5
    result = estimate_precision_lift_mde(short, alpha=0.05, target_power=0.8, seed=1)
    assert result["decision"] == "INCONCLUSIVE"


def test_walk_forward_folds_purge_actual_outcome_dates():
    sessions = pd.bdate_range("2024-01-01", periods=40)
    rows = []
    for day in range(30):
        rows.append({"signal_date":sessions[day],"outcome_end_date":sessions[min(day+2,39)]})
    folds = build_purged_walk_forward_folds(
        pd.DataFrame(rows), sessions, min_train_sessions=10,
        test_window_sessions=5, purge_sessions=6
    )
    assert folds
    first = folds[0]
    test_start = pd.Timestamp(first.test_start)
    train = pd.DataFrame(rows).iloc[list(first.train_indices)]
    assert (pd.to_datetime(train["outcome_end_date"]) < test_start - pd.Timedelta(days=0)).all()
    assert all(pd.Timestamp(x) < test_start for x in train["signal_date"])


def test_walk_forward_rejects_dates_outside_development_calendar():
    sessions = pd.bdate_range("2024-01-01", periods=20)
    frame = pd.DataFrame([{"signal_date":"2025-01-01","outcome_end_date":"2025-01-08"}])
    with pytest.raises(ValueError, match="outside"):
        build_purged_walk_forward_folds(frame, sessions, min_train_sessions=5, test_window_sessions=3)


def test_factor_gate_fails_closed_without_frozen_design_and_review():
    result = evaluate_factor_alpha_gate(
        alpha_lower_95=0.01, factor_definitions_frozen=False,
        inference_sensitivity_frozen=False, data_validated=False, human_reviewed=False
    )
    assert result["passed"] is False
    assert "factor_definitions_not_frozen" in result["blockers"]


def test_factor_gate_requires_positive_lower_confidence_bound():
    result = evaluate_factor_alpha_gate(
        alpha_lower_95=0.0, factor_definitions_frozen=True,
        inference_sensitivity_frozen=True, data_validated=True, human_reviewed=True
    )
    assert result["passed"] is False


def test_all_sixteen_gates_fail_closed_and_pilot_go_never_authorizes_deployment():
    gates = {i: True for i in range(1,17)}
    result = evaluate_all_pilot_gates(
        gates, upstream_data_validated=False,
        independent_human_reviewed=False, protocol_frozen=False
    )
    assert result["status"] == "RESEARCH_HOLD"
    assert result["promotion_eligible"] is False
    assert result["live_execution_enabled"] is False
    passed = evaluate_all_pilot_gates(
        gates, upstream_data_validated=True,
        independent_human_reviewed=True, protocol_frozen=True
    )
    assert passed["status"] == "ELIGIBLE_FOR_SEPARATELY_APPROVED_BROADER_EXPERIMENT"
    assert passed["pilot_go_authorizes_paper_trading"] is False


def test_source_manifest_compares_original_payload_hashes():
    payload = b"official source bytes"
    import hashlib
    digest = hashlib.sha256(payload).hexdigest()
    manifest = pd.DataFrame([{
        "source_id":"NSE-RAW-1","source_url":"https://nseindia.com/archive.pdf",
        "source_sha256":digest,"retrieved_at":"2024-01-02T10:00:00Z"
    }])
    result = verify_source_manifest_payloads(manifest, {"NSE-RAW-1":payload})
    assert result["passed"] is True
    assert result["verified_count"] == 1
    assert result["authenticity_verified"] is False
    corrupted = verify_source_manifest_payloads(manifest, {"NSE-RAW-1":b"modified"})
    assert corrupted["passed"] is False
    assert corrupted["hash_mismatches"] == ["NSE-RAW-1"]
