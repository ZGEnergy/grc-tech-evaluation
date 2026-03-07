"""Conftest providing FNM gating fixtures for this test directory."""

from __future__ import annotations

from pathlib import Path

import pytest

from fnm.scripts.fnm_gating_fixtures import (  # noqa: F401
    require_fnm,
    require_fnm_csvs,
    require_fnm_raw,
)


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "fnm: tests requiring FNM data (FNM_PATH env var)")
    config.addinivalue_line("markers", "octave: tests requiring Octave and MATPOWER installation")
    config.addinivalue_line(
        "markers", "gridcal: tests requiring VeraGridEngine (GridCal) installed"
    )


@pytest.fixture
def require_gridcal() -> dict:
    """Skip the test if VeraGridEngine (GridCal) is not installed.

    Returns a dict with useful paths for GridCal integration tests.
    """
    try:
        import VeraGridEngine  # noqa: F401
    except ImportError:
        pytest.skip("VeraGridEngine (GridCal) not installed")

    # Locate case39.m for integration tests
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    case39_path = repo_root / "data" / "networks" / "case39.m"

    return {
        "case39_path": case39_path,
    }
