"""Tests for fnm_gating_cli: CLI entry point (tests 10-12)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnm.scripts.fnm_gating_cli import cli_validate_fnm_path


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


def test_cli_exit_0_when_valid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit code 0 when FNM_PATH is valid with all files present."""
    fnm_dir = tmp_path / "fnm_data"
    fnm_dir.mkdir()
    file_names = ["test.raw", "bus_names.csv"]
    for name in file_names:
        (fnm_dir / name).write_text("stub", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(manifest_path, file_names)

    monkeypatch.setenv("FNM_PATH", str(fnm_dir))

    # Patch resolve_fnm_path to use our test manifest
    from fnm.scripts import fnm_gating_cli

    original_resolve = fnm_gating_cli.resolve_fnm_path

    def patched_resolve(**kwargs):
        kwargs["manifest_path"] = manifest_path
        return original_resolve(**kwargs)

    monkeypatch.setattr(fnm_gating_cli, "resolve_fnm_path", patched_resolve)

    exit_code = cli_validate_fnm_path([])
    assert exit_code == 0


def test_cli_exit_1_when_not_set(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit code 1 when FNM_PATH is not set, output includes 'not set'."""
    monkeypatch.delenv("FNM_PATH", raising=False)

    exit_code = cli_validate_fnm_path([])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "not set" in captured.out.lower()


def test_cli_output_lists_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Output includes [FOUND] and [MISSING] markers for file checks."""
    fnm_dir = tmp_path / "fnm_data"
    fnm_dir.mkdir()
    file_names = ["test.raw", "bus_names.csv", "costs.csv"]
    # Create only two files so one is missing
    (fnm_dir / "test.raw").write_text("stub", encoding="utf-8")
    (fnm_dir / "bus_names.csv").write_text("stub", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(manifest_path, file_names)

    monkeypatch.setenv("FNM_PATH", str(fnm_dir))

    from fnm.scripts import fnm_gating_cli

    original_resolve = fnm_gating_cli.resolve_fnm_path

    def patched_resolve(**kwargs):
        kwargs["manifest_path"] = manifest_path
        return original_resolve(**kwargs)

    monkeypatch.setattr(fnm_gating_cli, "resolve_fnm_path", patched_resolve)

    exit_code = cli_validate_fnm_path([])
    captured = capsys.readouterr()

    assert "[FOUND]" in captured.out
    assert "[MISSING]" in captured.out
    assert exit_code == 1  # partial means exit 1
