"""Tests for fnm_gating module: resolve_fnm_path and data structures (tests 1-6)."""

from __future__ import annotations

import json
from pathlib import Path

from fnm.scripts.fnm_gating import (
    FnmFileStatus,
    FnmPathStatus,
    resolve_fnm_path,
)


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


def test_resolve_not_set(monkeypatch: object, tmp_path: Path) -> None:
    """FNM_PATH not in env -> status=NOT_SET, fnm_path=None, empty file_checks."""
    import pytest

    mp = pytest.MonkeyPatch() if not hasattr(monkeypatch, "delenv") else monkeypatch
    mp.delenv("FNM_PATH", raising=False)  # type: ignore[union-attr]

    result = resolve_fnm_path(manifest_path=tmp_path / "manifest.json")

    assert result.status == FnmPathStatus.NOT_SET
    assert result.fnm_path is None
    assert result.file_checks == []
    assert not result.is_usable
    assert "not set" in result.skip_reason.lower()


def test_resolve_invalid_path(monkeypatch: object, tmp_path: Path) -> None:
    """FNM_PATH set to non-existent dir -> status=INVALID_PATH."""
    import pytest

    mp = pytest.MonkeyPatch() if not hasattr(monkeypatch, "setenv") else monkeypatch
    nonexistent = tmp_path / "does_not_exist"
    mp.setenv("FNM_PATH", str(nonexistent))  # type: ignore[union-attr]

    result = resolve_fnm_path(manifest_path=tmp_path / "manifest.json")

    assert result.status == FnmPathStatus.INVALID_PATH
    assert result.fnm_path is not None
    assert not result.is_usable


def test_resolve_valid_all_files(monkeypatch: object, tmp_path: Path) -> None:
    """FNM_PATH with all manifest files as stubs -> status=VALID, all FOUND."""
    import pytest

    mp = pytest.MonkeyPatch() if not hasattr(monkeypatch, "setenv") else monkeypatch

    fnm_dir = tmp_path / "fnm_data"
    fnm_dir.mkdir()
    file_names = ["test.raw", "bus_names.csv", "costs.csv"]
    for name in file_names:
        (fnm_dir / name).write_text("stub", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(manifest_path, file_names)

    mp.setenv("FNM_PATH", str(fnm_dir))  # type: ignore[union-attr]
    result = resolve_fnm_path(manifest_path=manifest_path)

    assert result.status == FnmPathStatus.VALID
    assert result.is_usable
    assert len(result.found_files) == 3
    assert len(result.missing_files) == 0
    for fc in result.file_checks:
        assert fc.status == FnmFileStatus.FOUND
        assert fc.absolute_path is not None


def test_resolve_partial_missing_csv(monkeypatch: object, tmp_path: Path) -> None:
    """RAW present but one CSV missing -> status=PARTIAL."""
    import pytest

    mp = pytest.MonkeyPatch() if not hasattr(monkeypatch, "setenv") else monkeypatch

    fnm_dir = tmp_path / "fnm_data"
    fnm_dir.mkdir()
    file_names = ["test.raw", "bus_names.csv", "costs.csv"]
    # Only create two of three files
    (fnm_dir / "test.raw").write_text("stub", encoding="utf-8")
    (fnm_dir / "bus_names.csv").write_text("stub", encoding="utf-8")
    # costs.csv is deliberately missing

    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(manifest_path, file_names)

    mp.setenv("FNM_PATH", str(fnm_dir))  # type: ignore[union-attr]
    result = resolve_fnm_path(manifest_path=manifest_path)

    assert result.status == FnmPathStatus.PARTIAL
    assert result.is_usable
    assert len(result.found_files) == 2
    assert len(result.missing_files) == 1
    assert result.missing_files[0].expected_name == "costs.csv"
    assert "missing" in result.skip_reason.lower()


def test_resolve_tilde_expansion(monkeypatch: object, tmp_path: Path) -> None:
    """FNM_PATH=~/fnm_data -> tilde expanded before validation."""
    import pytest

    mp = pytest.MonkeyPatch() if not hasattr(monkeypatch, "setenv") else monkeypatch

    # Create a directory under a fake HOME
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    fnm_dir = fake_home / "fnm_data"
    fnm_dir.mkdir()
    file_names = ["test.raw"]
    (fnm_dir / "test.raw").write_text("stub", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(manifest_path, file_names)

    mp.setenv("HOME", str(fake_home))  # type: ignore[union-attr]
    mp.setenv("FNM_PATH", "~/fnm_data")  # type: ignore[union-attr]
    result = resolve_fnm_path(manifest_path=manifest_path)

    assert result.status == FnmPathStatus.VALID
    assert result.fnm_path is not None
    assert "~" not in str(result.fnm_path)
    assert result.fnm_path.is_absolute()


def test_resolve_manifest_not_found(monkeypatch: object, tmp_path: Path) -> None:
    """Explicit manifest_path to non-existent file -> status=MANIFEST_ERROR."""
    import pytest

    mp = pytest.MonkeyPatch() if not hasattr(monkeypatch, "setenv") else monkeypatch

    fnm_dir = tmp_path / "fnm_data"
    fnm_dir.mkdir()
    mp.setenv("FNM_PATH", str(fnm_dir))  # type: ignore[union-attr]

    result = resolve_fnm_path(manifest_path=tmp_path / "nonexistent_manifest.json")

    assert result.status == FnmPathStatus.MANIFEST_ERROR
    assert not result.is_usable
    assert "manifest" in result.skip_reason.lower()
