"""Smoke tests verifying Ipopt and GLPK solver availability for pandapower."""

from __future__ import annotations

import subprocess

import pandapower as pp
import pandapower.networks as pn


class TestSolvers:
    def test_ipopt_binary(self) -> None:
        result = subprocess.run(["ipopt", "--version"], capture_output=True)
        assert result.returncode == 0

    def test_glpk_binary(self) -> None:
        result = subprocess.run(["glpsol", "--version"], capture_output=True)
        assert result.returncode == 0

    def test_pandapower_opf_ipopt(self) -> None:
        net = pn.case39()
        # Add polynomial cost curves required by OPF
        for gidx in net.gen.index:
            pp.create_poly_cost(net, gidx, "gen", cp1_eur_per_mw=1.0)
        for eidx in net.ext_grid.index:
            pp.create_poly_cost(net, eidx, "ext_grid", cp1_eur_per_mw=1.0)

        pp.runopp(net, solver="ipopt")
        assert net["OPF_converged"]
