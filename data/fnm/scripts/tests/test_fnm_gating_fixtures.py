"""Tests for fnm_gating_fixtures: pytest fixtures (tests 7-9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnm.scripts.fnm_gating import FnmPathResult, FnmPathStatus, resolve_fnm_path


def _write_test_manifest(manifest_path: Path, file_names: list[str]) -> None:
    """Write a minimal test manifest with the given filenames."""
    source_files = []
    for name in file_names:
        file_type = "psse_raw" if name.endswith(".raw") else "supplemental_csv"
        source_files.append(
            {
                "file_name": name,
                "file_type": file_type,
                "description": f"Test file {name}",
                "sha256": None,
                "required": True,
            }
        )
    data = {
        "version": "1.0",
        "variant": "TEST",
        "source_files": source_files,
        "notes": "test manifest",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_fixture_skips_when_not_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """require_fnm raises pytest.skip with 'FNM_PATH' and 'not set' when unset."""
    monkeypatch.delenv("FNM_PATH", raising=False)

    result = resolve_fnm_path(manifest_path=tmp_path / "manifest.json")
    assert result.status == FnmPathStatus.NOT_SET

    with pytest.raises(pytest.skip.Exception) as exc_info:
        if not result.is_usable:
            pytest.skip(result.skip_reason)

    skip_msg = str(exc_info.value)
    assert "FNM_PATH" in skip_msg
    assert "not set" in skip_msg


def test_fixture_returns_result_when_valid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """require_fnm returns FnmPathResult with status=VALID when properly configured."""
    fnm_dir = tmp_path / "fnm_data"
    fnm_dir.mkdir()
    file_names = ["test.raw", "bus_names.csv"]
    for name in file_names:
        (fnm_dir / name).write_text("stub", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(manifest_path, file_names)

    monkeypatch.setenv("FNM_PATH", str(fnm_dir))
    result = resolve_fnm_path(manifest_path=manifest_path)

    # Simulate what the fixture does
    assert result.is_usable
    assert isinstance(result, FnmPathResult)
    assert result.status == FnmPathStatus.VALID


def test_fixture_skip_message_contains_instructions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Skip message includes 'data/fnm/README.md' for setup instructions."""
    monkeypatch.delenv("FNM_PATH", raising=False)

    result = resolve_fnm_path(manifest_path=tmp_path / "manifest.json")
    assert result.status == FnmPathStatus.NOT_SET

    skip_reason = result.skip_reason
    assert "data/fnm/README.md" in skip_reason
    assert "FNM_PATH" in skip_reason
