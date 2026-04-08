"""Pytest fixtures for FNM_PATH gating.

Provides reusable fixtures that skip tests gracefully when FNM data is unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fnm.scripts.fnm_gating import FnmFileStatus, FnmPathResult, resolve_fnm_path


@pytest.fixture
def require_fnm() -> FnmPathResult:
    """Skip the test if FNM data is unavailable. Returns FnmPathResult when usable."""
    result = resolve_fnm_path()
    if not result.is_usable:
        pytest.skip(result.skip_reason)
    return result


@pytest.fixture
def require_fnm_raw(require_fnm: FnmPathResult) -> Path:
    """Return the absolute path to the PSS/E RAW file. Skip if not found.

    Depends on ``require_fnm`` to ensure FNM_PATH is validated first.
    """
    for fc in require_fnm.file_checks:
        if fc.expected_name.endswith(".raw") and fc.status == FnmFileStatus.FOUND:
            assert fc.absolute_path is not None
            return fc.absolute_path
    pytest.skip("PSS/E RAW file not found in FNM_PATH.")
    # unreachable, but satisfies type checker
    raise AssertionError  # pragma: no cover


@pytest.fixture
def require_fnm_csvs(require_fnm: FnmPathResult) -> dict[str, Path]:
    """Return a dict of CSV filename -> absolute path for found CSVs.

    Only includes CSV files that were actually found on disk.
    Depends on ``require_fnm`` to ensure FNM_PATH is validated first.
    """
    csvs: dict[str, Path] = {}
    for fc in require_fnm.file_checks:
        if (
            fc.expected_name.endswith(".csv")
            and fc.status == FnmFileStatus.FOUND
            and fc.absolute_path is not None
        ):
            csvs[fc.expected_name] = fc.absolute_path
    return csvs


def get_conftest_template() -> str:
    """Return conftest.py content that imports FNM gating fixtures.

    Downstream test directories can use this as a template or copy it directly
    into their ``conftest.py``.
    """
    return '''\
"""Conftest providing FNM gating fixtures for this test directory."""

from __future__ import annotations

from fnm.scripts.fnm_gating_fixtures import require_fnm, require_fnm_csvs, require_fnm_raw

__all__ = ["require_fnm", "require_fnm_csvs", "require_fnm_raw"]
'''
