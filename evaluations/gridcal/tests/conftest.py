"""Shared fixtures for gridcal gate and rubric-dimension tests."""

from __future__ import annotations

from pathlib import Path

import pytest

# evaluations/gridcal/tests/conftest.py -> evaluations/gridcal/tests/
#   -> evaluations/gridcal/ -> evaluations/ -> repo root -> data/networks/
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "networks"


@pytest.fixture
def data_dir() -> Path:
    """Path to the shared network data directory."""
    assert DATA_DIR.is_dir(), f"Data directory not found: {DATA_DIR}"
    return DATA_DIR
