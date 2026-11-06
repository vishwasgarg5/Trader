import pandas as pd
import pytest

from trader import experiment


def test_experiment_module_imports_path_for_snapshot_evidence_resolution():
    from pathlib import Path

    assert experiment.Path is Path


def test_run_experiment_fails_closed_before_download_when_pit_evidence_is_incomplete(monkeypatch):
    monkeypatch.setattr(experiment, "download_prices", lambda *args, **kwargs: pytest.fail(
        "market data download must not run before point-in-time evidence is complete"
    ))
    monkeypatch.setattr(
        experiment, "download_delivery_history",
        lambda *args, **kwargs: pytest.fail("delivery download must not run"),
    )
    monkeypatch.setattr(
        experiment, "build_experiment_frame",
        lambda *args, **kwargs: pytest.fail("feature build must not run"),
    )

    with pytest.raises(RuntimeError, match="T-0003 full point-in-time Nifty 50 evidence gate is BLOCKED"):
        experiment.run_experiment()


def test_run_experiment_requires_interval_panel_even_if_event_gate_passes(monkeypatch, tmp_path):
    monkeypatch.setattr(experiment, "DATA", tmp_path)
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "nifty50_transition_register.csv").write_text("placeholder", encoding="utf-8")
    (reference / "nifty50_annual_coverage.csv").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(experiment, "audit_special_membership_events", lambda *args: {\n        "ready": True, "errors": [],\n    })\n    monkeypatch.setattr(experiment, "audit_membership_evidence", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "audit_security_aliases", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "audit_corporate_action_ledger", lambda *args: {
        "corporate_action_adjustment_verified": True,
    })
    monkeypatch.setattr(experiment, "download_prices", lambda *args, **kwargs: pytest.fail(
        "market data download must not run without verified membership intervals"
    ))

    with pytest.raises(RuntimeError, match="universe_membership.csv"):
        experiment.run_experiment()



def test_run_experiment_requires_verified_security_identity_before_download(monkeypatch, tmp_path):
    monkeypatch.setattr(experiment, "DATA", tmp_path)
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "nifty50_transition_register.csv").write_text("placeholder", encoding="utf-8")
    (reference / "nifty50_annual_coverage.csv").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(experiment, "audit_special_membership_events", lambda *args: {\n        "ready": True, "errors": [],\n    })\n    monkeypatch.setattr(experiment, "audit_membership_evidence", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "audit_security_aliases", lambda *args: {
        "ready": False, "errors": ["LTM: identity mapping is not VERIFIED"],
    })
    monkeypatch.setattr(experiment, "download_prices", lambda *args, **kwargs: pytest.fail(
        "market data download must not run while security identity is unresolved"
    ))

    with pytest.raises(RuntimeError, match="security identity gate is BLOCKED"):
        experiment.run_experiment()



def test_run_experiment_requires_verified_corporate_action_treatment(monkeypatch, tmp_path):
    monkeypatch.setattr(experiment, "DATA", tmp_path)
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "nifty50_transition_register.csv").write_text("placeholder", encoding="utf-8")
    (reference / "nifty50_annual_coverage.csv").write_text("placeholder", encoding="utf-8")
    (reference / "corporate_actions.csv").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(experiment, "audit_special_membership_events", lambda *args: {\n        "ready": True, "errors": [],\n    })\n    monkeypatch.setattr(experiment, "audit_membership_evidence", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "audit_security_aliases", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "audit_corporate_action_ledger", lambda *args: {
        "corporate_action_adjustment_verified": False,
    })
    monkeypatch.setattr(experiment, "download_prices", lambda *args, **kwargs: pytest.fail(
        "market data download must not run while corporate-action treatment is unresolved"
    ))

    with pytest.raises(RuntimeError, match="corporate-action gate is BLOCKED"):
        experiment.run_experiment()



def test_point_in_time_universe_loader_includes_historical_constituents(tmp_path):
    path = tmp_path / "universe_membership.csv"
    pd.DataFrame([
        {"symbol": "CURRENT.NS", "valid_from": "2024-01-01", "valid_to": ""},
        {"symbol": "FORMER.NS", "valid_from": "2018-04-01", "valid_to": "2020-01-01"},
        {"symbol": "CURRENT.NS", "valid_from": "2020-01-01", "valid_to": ""},
    ]).to_csv(path, index=False)

    assert experiment.load_point_in_time_universe(path) == ["CURRENT.NS", "FORMER.NS"]


def test_experiment_downloads_all_symbols_from_pit_ledger_not_static_config(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    reference = data_root / "reference"
    reference.mkdir(parents=True)
    membership = pd.DataFrame([
        {"symbol": "CURRENT.NS", "valid_from": "2024-01-01", "valid_to": ""},
        {"symbol": "FORMER.NS", "valid_from": "2018-04-01", "valid_to": "2020-01-01"},
    ])
    membership.to_csv(reference / "universe_membership.csv", index=False)
    (reference / "nifty50_transition_register.csv").write_text("placeholder", encoding="utf-8")
    (reference / "nifty50_annual_coverage.csv").write_text("placeholder", encoding="utf-8")
    (reference / "corporate_actions.csv").write_text("placeholder", encoding="utf-8")
    (reference / "security_symbol_aliases.csv").write_text("placeholder", encoding="utf-8")
    config = tmp_path / "config"
    config.mkdir()
    (config / "sector_classifications.json").write_text(
        '{"classification_as_of":"2026-01-01","source_url":"https://example.com",'
        '"note":"test fixture","symbols":{"CURRENT.NS":"A","FORMER.NS":"B"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(experiment, "DATA", data_root)
    monkeypatch.setattr(experiment, "audit_special_membership_events", lambda *args: {\n        "ready": True, "errors": [],\n    })\n    monkeypatch.setattr(experiment, "audit_membership_evidence", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "audit_security_aliases", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "audit_corporate_action_ledger", lambda *args: {
        "corporate_action_adjustment_verified": True,
    })
    monkeypatch.setattr(experiment, "load_universe", lambda: pytest.fail(
        "research experiment must not load the legacy static ticker file"
    ))
    seen = {}

    def stop_after_download(tickers, period):
        seen["tickers"] = tickers
        seen["period"] = period
        raise RuntimeError("stop after asserting PIT universe")

    monkeypatch.setattr(experiment, "download_prices", stop_after_download)
    with pytest.raises(RuntimeError, match="stop after asserting PIT universe"):
        experiment.run_experiment()

    assert seen["tickers"] == ["CURRENT.NS", "FORMER.NS"]
    assert seen["period"] == "7y"
