"""Smoke tests verifying Ipopt and GLPK solver availability for PyPSA."""

from __future__ import annotations

import subprocess


class TestSolvers:
    def test_ipopt_binary(self) -> None:
        result = subprocess.run(["ipopt", "--version"], capture_output=True)
        assert result.returncode == 0

    def test_glpk_binary(self) -> None:
        result = subprocess.run(["glpsol", "--version"], capture_output=True)
        assert result.returncode == 0

    def test_pypsa_optimize_glpk(self) -> None:
        import pypsa

        n = pypsa.Network()
        n.add("Bus", "bus")
        n.add("Generator", "gen", bus="bus", p_nom=100.0, marginal_cost=1.0)
        n.add("Load", "load", bus="bus", p_set=50.0)
        n.snapshots = [0]

        status, condition = n.optimize(solver_name="glpk")
        assert condition == "optimal"
