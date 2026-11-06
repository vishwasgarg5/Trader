from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


def build_data_snapshot_manifest(
    files: Iterable[Path],
    *,
    root: Path,
    metadata: dict | None = None,
) -> dict:
    """Build a deterministic SHA-256 manifest for frozen research inputs."""
    root = Path(root).resolve()
    entries = []
    for item in sorted((Path(p) for p in files), key=lambda p: str(p)):
        path = item if item.is_absolute() else root / item
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Snapshot input is missing: {path}")
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError(f"Snapshot input must be inside root: {path}") from exc
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": digest,
        })
    if not entries:
        raise ValueError("At least one snapshot input is required")
    return {
        "schema_version": 1,
        "metadata": dict(metadata or {}),
        "file_count": len(entries),
        "files": entries,
    }


def write_data_snapshot_manifest(
    files: Iterable[Path],
    output_path: Path,
    *,
    root: Path,
    metadata: dict | None = None,
) -> dict:
    """Write and return a stable JSON manifest for frozen research inputs."""
    manifest = build_data_snapshot_manifest(files, root=root, metadata=metadata)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
