import json
from pathlib import Path

import pytest

from trader.atomic import write_bytes_atomic, write_json_atomic, write_text_atomic


def test_atomic_text_and_bytes_replace_existing_file(tmp_path):
    target = tmp_path / "nested" / "value.txt"
    write_text_atomic(target, "first")
    write_bytes_atomic(target, b"second")
    assert target.read_bytes() == b"second"
    assert not list(target.parent.glob("*.tmp"))
    assert not list(target.parent.glob(".*.tmp"))


def test_atomic_json_is_stable_and_rejects_nan(tmp_path):
    target = tmp_path / "value.json"
    write_json_atomic(target, {"b": 2, "a": 1})
    assert target.read_text() == '{\n  "a": 1,\n  "b": 2\n}\n'
    with pytest.raises(ValueError):
        write_json_atomic(target, {"bad": float("nan")})


def test_writer_rejects_wrong_types(tmp_path):
    with pytest.raises(TypeError):
        write_bytes_atomic(tmp_path / "x", "not bytes")
    with pytest.raises(TypeError):
        write_text_atomic(tmp_path / "x", b"not text")
