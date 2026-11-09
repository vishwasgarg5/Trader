"""Crash-safe, same-filesystem atomic file writers."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_bytes_atomic(path: str | Path, content: bytes) -> None:
    """Atomically replace *path* with bytes, fsyncing file and parent directory."""
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
        try:
            dir_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            # Some platforms/filesystems do not support directory fsync.
            pass
    except BaseException:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise


def write_text_atomic(path: str | Path, content: str, *, encoding: str = "utf-8") -> None:
    if not isinstance(content, str):
        raise TypeError("content must be str")
    write_bytes_atomic(path, content.encode(encoding))


def write_json_atomic(path: str | Path, value: Any) -> None:
    write_text_atomic(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
