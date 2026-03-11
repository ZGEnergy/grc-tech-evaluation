"""Tests for report Python dependency locking."""

from __future__ import annotations

from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent
LOCKFILE_PATH = REPORT_DIR / "uv.lock"


def test_uv_lock_uses_public_pypi() -> None:
    """The report lockfile must not depend on the private package registry."""
    text = LOCKFILE_PATH.read_text()
    assert "pkg.dev" not in text
    assert "zge-python-repo" not in text
    assert 'registry = "https://pypi.org/simple"' in text
