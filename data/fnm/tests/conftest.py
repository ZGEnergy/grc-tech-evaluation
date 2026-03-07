"""Conftest providing FNM gating fixtures for this test directory."""

from __future__ import annotations

import pytest

from fnm.scripts.fnm_gating_fixtures import (  # noqa: F401
    require_fnm,
    require_fnm_csvs,
    require_fnm_raw,
)


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "fnm: tests requiring FNM data (FNM_PATH env var)")
