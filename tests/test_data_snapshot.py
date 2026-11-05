import hashlib

import pytest

from trader.data_snapshot import build_data_snapshot_manifest, write_data_snapshot_manifest


def test_snapshot_manifest_records_stable_sha256_and_size(tmp_path):
    source = tmp_path / "prices.csv"
    source.write_bytes(b"date,symbol,close\n2026-01-01,AAA,100\n")
    manifest = build_data_snapshot_manifest(
        [source], root=tmp_path, metadata={"commit": "abc123"},
    )
    assert manifest["file_count"] == 1
    assert manifest["files"][0]["path"] == "prices.csv"
    assert manifest["files"][0]["size_bytes"] == source.stat().st_size
    assert manifest["files"][0]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["metadata"]["commit"] == "abc123"


def test_snapshot_manifest_fails_closed_for_missing_or_external_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_data_snapshot_manifest(["missing.csv"], root=tmp_path)
    outside = tmp_path.parent / "outside.csv"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="inside root"):
        build_data_snapshot_manifest([outside], root=tmp_path)


def test_snapshot_writer_persists_manifest(tmp_path):
    source = tmp_path / "delivery.csv"
    source.write_text("date,symbol,delivery_pct\n", encoding="utf-8")
    target = tmp_path / "manifest.json"
    manifest = write_data_snapshot_manifest(
        [source], target, root=tmp_path, metadata={"dataset": "nse-delivery"},
    )
    assert target.is_file()
    assert '"dataset": "nse-delivery"' in target.read_text(encoding="utf-8")
    assert manifest["file_count"] == 1
