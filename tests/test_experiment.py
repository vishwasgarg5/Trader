import pandas as pd
import pytest

from trader import experiment


def test_experiment_module_imports_path_for_snapshot_evidence_resolution():
    from pathlib import Path

    assert experiment.Path is Path


def test_run_experiment_fails_closed_before_feature_build_on_missing_universe_symbol(monkeypatch):
    monkeypatch.setattr(experiment, "load_universe", lambda: ["TATAMOTORS.NS"])
    monkeypatch.setattr(experiment, "download_prices", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        experiment, "download_delivery_history",
        lambda *args, **kwargs: pytest.fail("delivery download must not run"),
    )
    monkeypatch.setattr(
        experiment, "build_experiment_frame",
        lambda *args, **kwargs: pytest.fail("feature build must not run on an incomplete universe"),
    )

    with pytest.raises(RuntimeError, match="TATAMOTORS.NS"):
        experiment.run_experiment()
