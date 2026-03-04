"""
Shared pytest fixtures for power-system tool evaluation.

Copy this file into evaluations/<tool>/tests/ to enable pytest discovery
and shared fixtures across test dimensions.
"""

import json
from pathlib import Path

import pytest

# Repository root (3 levels up from evaluations/<tool>/tests/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "networks"

# Network file paths
NETWORKS = {
    "TINY": DATA_DIR / "case39.m",
    "SMALL": DATA_DIR / "case_ACTIVSg2000.m",
    "MEDIUM": DATA_DIR / "case_ACTIVSg10k.m",
}

# Expected bus/branch/gen counts for gate validation
REFERENCE_COUNTS = {
    "TINY": {"buses": 39, "branches": 46, "generators": 10},
    # SMALL and MEDIUM counts verified at gate time
}


@pytest.fixture
def network_file_tiny():
    """Path to the TINY (IEEE 39-bus) network file."""
    path = NETWORKS["TINY"]
    assert path.exists(), f"TINY network file not found: {path}"
    return str(path)


@pytest.fixture
def network_file_small():
    """Path to the SMALL (ACTIVSg 2k) network file."""
    path = NETWORKS["SMALL"]
    assert path.exists(), f"SMALL network file not found: {path}"
    return str(path)


@pytest.fixture
def network_file_medium():
    """Path to the MEDIUM (ACTIVSg 10k) network file."""
    path = NETWORKS["MEDIUM"]
    assert path.exists(), f"MEDIUM network file not found: {path}"
    return str(path)


@pytest.fixture
def results_dir(request):
    """Create and return the results directory for the current test dimension.

    Infers the dimension from the test file's parent directory name.
    """
    test_file = Path(request.fspath)
    dimension = test_file.parent.name
    tool_dir = test_file.parent.parent.parent
    results = tool_dir / "results" / dimension
    results.mkdir(parents=True, exist_ok=True)
    return results


@pytest.fixture
def write_result(results_dir):
    """Fixture that returns a function to write a test result file."""

    def _write(test_id: str, result: dict, tier: str | None = None):
        suffix = f"_{tier}" if tier else ""
        path = results_dir / f"{test_id}{suffix}.json"
        path.write_text(json.dumps(result, indent=2, default=str))
        return path

    return _write


def pytest_collection_modifyitems(config, items):
    """Sort tests by test ID for consistent execution order."""
    items.sort(key=lambda item: item.name)
