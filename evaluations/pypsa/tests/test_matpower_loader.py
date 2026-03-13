"""
Tests for the shared MATPOWER loader utility (matpower_loader.load_pypsa).

Verifies that both correctness patches are applied after loading:
  1. Transformer susceptance: b = 1/x (not 1/(x*tap))
  2. Generator marginal costs populated from gencost data

These tests run in CI as part of the pypsa evaluation suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure evaluations/shared/ is importable (existing conftest.py predates this loader)
# Path: tests/ -> pypsa/ -> evaluations/ -> shared/
_SHARED_DIR = Path(__file__).resolve().parent.parent.parent / "shared"
if _SHARED_DIR.exists() and str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from matpower_loader import load_pypsa  # noqa: E402


@pytest.fixture
def tiny_network(data_dir: Path) -> str:
    path = data_dir / "case39.m"
    assert path.exists(), f"TINY network not found: {path}"
    return str(path)


class TestLoadPypsa:
    """Verify load_pypsa() applies both post-load correctness patches."""

    def test_marginal_costs_populated(self, tiny_network: str) -> None:
        """All generators have positive marginal costs from gencost data."""
        n = load_pypsa(tiny_network)
        mc = n.generators["marginal_cost"]
        assert (mc > 0).all(), (
            f"Expected all generators to have marginal_cost > 0; "
            f"got zeros for: {mc[mc <= 0].index.tolist()}"
        )

    def test_transformer_count(self, tiny_network: str) -> None:
        """Network loads with transformers present."""
        n = load_pypsa(tiny_network)
        assert len(n.transformers) > 0, "Expected at least one transformer in case39"

    def test_transformer_susceptance_patch(self, tiny_network: str) -> None:
        """Transformer susceptance equals 1/x (MATPOWER DC convention), not 1/(x*tap)."""
        import numpy as np

        n = load_pypsa(tiny_network)
        for t_id in n.transformers.index:
            x = n.transformers.at[t_id, "x"]
            b = n.transformers.at[t_id, "b"]
            if x != 0:
                expected_b = 1.0 / x
                assert np.isclose(b, expected_b, rtol=1e-6), (
                    f"Transformer {t_id}: b={b:.6f} but expected 1/x={expected_b:.6f} (x={x:.6f})"
                )

    def test_lpf_converges(self, tiny_network: str) -> None:
        """Linear power flow runs without error after loading."""
        n = load_pypsa(tiny_network)
        n.lpf()  # raises on failure
        assert "v_ang" in n.buses_t, "Expected bus angle results after lpf()"

    def test_overwrite_zero_s_nom_kwarg(self, tiny_network: str) -> None:
        """overwrite_zero_s_nom kwarg is passed through without error."""
        n = load_pypsa(tiny_network, overwrite_zero_s_nom=100000.0)
        assert len(n.buses) > 0
