"""Gate tests for GridCal: import, parse IEEE 39-bus case, solve DC power flow."""

from __future__ import annotations

from pathlib import Path


class TestGate:
    """Gate tests verifying GridCal (VeraGridEngine) can import, parse, and solve DCPF."""

    def test_import(self) -> None:
        """VeraGridEngine core library can be imported."""
        import importlib.metadata

        import VeraGridEngine as vge  # noqa: F401

        version = importlib.metadata.version("veragridengine")
        assert isinstance(version, str)
        assert len(version) > 0

    def test_parse_case39(self, data_dir: Path) -> None:
        """IEEE 39-bus MATPOWER case file parses into a GridCal MultiCircuit."""
        import VeraGridEngine as vge

        grid = vge.open_file(str(data_dir / "case39.m"))

        assert grid.get_bus_number() == 39, f"Expected 39 buses, got {grid.get_bus_number()}"
        assert grid.get_branch_number() > 0, "No branches loaded"

    def test_dc_power_flow(self, data_dir: Path) -> None:
        """DC power flow (Linear solver) solves successfully on IEEE 39-bus case."""
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        grid = vge.open_file(str(data_dir / "case39.m"))
        opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        results = vge.power_flow(grid, options=opts)

        assert results.converged, "DC power flow did not converge"
