"""
Shared pytest fixtures for power-system tool evaluation.

Copy this file into evaluations/<tool>/tests/ to enable pytest discovery
and shared fixtures across test dimensions.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

# Repository root (3 levels up from evaluations/<tool>/tests/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Make evaluations/shared/ importable for the shared MATPOWER loader.
_SHARED_DIR = REPO_ROOT / "shared"
if _SHARED_DIR.exists() and str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

DATA_DIR = REPO_ROOT / "data" / "networks"

# Network file paths
NETWORKS = {
    "TINY": DATA_DIR / "case39.m",
    "SMALL": DATA_DIR / "case_ACTIVSg2000.m",
    "MEDIUM": DATA_DIR / "case_ACTIVSg10k.m",
}
TIMESERIES = {
    "TINY": DATA_DIR.parent / "timeseries" / "case39",
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
    """Fixture that returns a function to write a test result markdown file.

    Produces markdown files with YAML frontmatter matching result-template.md.
    The ``result`` dict must contain at minimum ``test_id``, ``tool``,
    ``dimension``, ``status``, and a ``body`` key with the markdown content.
    All other keys are written as YAML frontmatter fields.
    """

    def _write(test_id: str, result: dict, tier: str | None = None):
        suffix = f"_{tier}" if tier else ""
        slug = result.get("slug", "")
        slug_part = f"_{slug}" if slug else ""
        path = results_dir / f"{test_id}{slug_part}{suffix}.md"

        body = result.pop("body", "")
        frontmatter = {k: v for k, v in result.items() if k != "slug"}
        frontmatter.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        content = (
            "---\n"
            + yaml.dump(frontmatter, default_flow_style=False)
            + "---\n\n"
            + body
        )
        path.write_text(content)
        return path

    return _write


def pytest_collection_modifyitems(config, items):
    """Sort tests by test ID for consistent execution order."""
    items.sort(key=lambda item: item.name)
