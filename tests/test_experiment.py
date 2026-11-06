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
    monkeypatch.setattr(experiment, "audit_membership_evidence", lambda *args: {
        "ready": True, "errors": [],
    })
    monkeypatch.setattr(experiment, "download_prices", lambda *args, **kwargs: pytest.fail(
        "market data download must not run without verified membership intervals"
    ))

    with pytest.raises(RuntimeError, match="universe_membership.csv"):
        experiment.run_experiment()
