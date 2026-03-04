"""Gate tests for PyPSA: import, parse IEEE 39-bus case, solve DC power flow."""

from __future__ import annotations

from pathlib import Path


class TestGate:
    """Gate tests verifying PyPSA can import, parse MATPOWER data, and solve DCPF."""

    def test_import(self) -> None:
        """PyPSA core library can be imported."""
        import pypsa

        assert hasattr(pypsa, "__version__")
        assert isinstance(pypsa.__version__, str)

    def test_parse_case39(self, data_dir: Path) -> None:
        """IEEE 39-bus MATPOWER case file parses into a PyPSA Network."""
        import pypsa
        from matpowercaseframes import CaseFrames

        cf = CaseFrames(str(data_dir / "case39.m"))
        ppc = {
            "version": "2",
            "baseMVA": cf.baseMVA,
            "bus": cf.bus.values,
            "gen": cf.gen.values,
            "branch": cf.branch.values,
        }

        net = pypsa.Network()
        net.import_from_pypower_ppc(ppc)

        assert len(net.buses) == 39, f"Expected 39 buses, got {len(net.buses)}"
        assert len(net.lines) + len(net.transformers) > 0, "No lines or transformers loaded"

    def test_dc_power_flow(self, data_dir: Path) -> None:
        """DC power flow (lpf) solves successfully on IEEE 39-bus case."""
        import pypsa
        from matpowercaseframes import CaseFrames

        cf = CaseFrames(str(data_dir / "case39.m"))
        ppc = {
            "version": "2",
            "baseMVA": cf.baseMVA,
            "bus": cf.bus.values,
            "gen": cf.gen.values,
            "branch": cf.branch.values,
        }

        net = pypsa.Network()
        net.import_from_pypower_ppc(ppc)
        net.lpf()

        v_ang = net.buses_t.v_ang
        assert not v_ang.empty, "No voltage angle results from lpf()"
        assert (v_ang.abs() > 0).any().any(), "All voltage angles are zero -- solver did not run"

        if len(net.lines) > 0:
            p0 = net.lines_t.p0
            assert not p0.empty, "No line power flow results from lpf()"
            assert (p0.abs() > 0).any().any(), "All line power flows are zero"
