"""Gate tests for pandapower: import, parse IEEE 39-bus case, solve DC power flow."""

from __future__ import annotations

from pathlib import Path


class TestGate:
    """Gate tests verifying pandapower can import, parse MATPOWER data, and solve DCPF."""

    def test_import(self) -> None:
        """pandapower core library can be imported."""
        import pandapower as pp

        assert hasattr(pp, "__version__")
        assert isinstance(pp.__version__, str)

    def test_parse_case39(self, data_dir: Path) -> None:
        """IEEE 39-bus MATPOWER case file parses into a pandapower network."""
        from pandapower.converter.matpower.from_mpc import from_mpc

        net = from_mpc(str(data_dir / "case39.m"))

        assert len(net.bus) == 39, f"Expected 39 buses, got {len(net.bus)}"
        total_branches = len(net.line) + len(net.trafo)
        assert total_branches == 46, f"Expected 46 branches (lines+trafos), got {total_branches}"

    def test_dc_power_flow(self, data_dir: Path) -> None:
        """DC power flow (rundcpp) solves successfully on IEEE 39-bus case."""
        import pandapower as pp
        from pandapower.converter.matpower.from_mpc import from_mpc

        net = from_mpc(str(data_dir / "case39.m"))
        pp.rundcpp(net)

        assert net.converged, "DC power flow did not converge"
        assert not net.res_bus.empty, "No bus results after rundcpp"
        assert not net.res_line.empty, "No line results after rundcpp"
        assert (net.res_bus["va_degree"].abs() > 0).any(), (
            "All bus voltage angles are zero -- solver did not run"
        )
