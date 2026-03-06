"""Gate tests for PyPSA: network ingestion at TINY, SMALL, and MEDIUM tiers.

Import method: matpowercaseframes.CaseFrames -> pypsa.Network.import_from_pypower_ppc

PyPSA has no native MATPOWER .m file reader.  The matpowercaseframes package
parses the .m file into DataFrames, which are converted to a pypower-style ppc
dict and imported via PyPSA's import_from_pypower_ppc().

Note: PyPSA's pypower importer does NOT import gencost data (areas, gencosts,
and component status are explicitly unsupported).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

# Reference counts verified via Octave/MATPOWER:
#   size(mpc.bus,1), size(mpc.branch,1), size(mpc.gen,1)
REFERENCE = {
    "G-1": {
        "file": "case39.m",
        "label": "IEEE 39-bus (TINY)",
        "buses": 39,
        "branches": 46,
        "generators": 10,
    },
    "G-2": {
        "file": "case_ACTIVSg2000.m",
        "label": "ACTIVSg 2000 (SMALL)",
        "buses": 2000,
        "branches": 3206,
        "generators": 544,
    },
    "G-3": {
        "file": "case_ACTIVSg10k.m",
        "label": "ACTIVSg 10000 (MEDIUM)",
        "buses": 10000,
        "branches": 12706,
        "generators": 2485,
    },
}


def _load_network(filepath: str):
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(filepath)
    ppc: dict = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    if hasattr(cf, "gencost") and cf.gencost is not None:
        ppc["gencost"] = cf.gencost.values

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net


class TestGate:
    """Gate tests verifying PyPSA can ingest MATPOWER networks at three tiers."""

    @pytest.mark.parametrize(
        "test_id",
        ["G-1", "G-2", "G-3"],
        ids=["G-1_ingest_tiny", "G-2_ingest_small", "G-3_ingest_medium"],
    )
    def test_ingest(self, data_dir: Path, test_id: str) -> None:
        """Load MATPOWER .m file and verify bus/branch/gen counts + data quality."""
        ref = REFERENCE[test_id]
        filepath = str(data_dir / ref["file"])

        t0 = time.perf_counter()
        net = _load_network(filepath)
        load_time = time.perf_counter() - t0

        actual_buses = len(net.buses)
        actual_branches = len(net.lines) + len(net.transformers)
        actual_generators = len(net.generators)

        # Print details for report capture
        print(f"\n--- {test_id}: {ref['label']} ---")
        print(f"Load time: {load_time:.3f}s")
        print(
            f"Expected: {ref['buses']} buses / "
            f"{ref['branches']} branches / {ref['generators']} gens"
        )
        print(
            f"Actual:   {actual_buses} buses / "
            f"{actual_branches} branches / {actual_generators} gens"
        )
        print(f"  Lines: {len(net.lines)}, Transformers: {len(net.transformers)}")

        # --- Count assertions ---
        assert actual_buses == ref["buses"], (
            f"Bus count mismatch: expected {ref['buses']}, got {actual_buses}"
        )
        assert actual_branches == ref["branches"], (
            f"Branch count mismatch: expected {ref['branches']}, got {actual_branches}"
        )
        assert actual_generators == ref["generators"], (
            f"Generator count mismatch: expected {ref['generators']}, got {actual_generators}"
        )

        # --- Data quality checks (warn, don't fail) ---
        warnings: list[str] = []

        # Bus voltage
        v_nom = net.buses.v_nom
        if v_nom.isna().any():
            warnings.append(f"NaN in bus v_nom: {v_nom.isna().sum()} buses")
        if np.isinf(v_nom).any():
            warnings.append(f"Inf in bus v_nom: {np.isinf(v_nom).sum()} buses")

        # Branch ratings
        if len(net.lines) > 0:
            zero_lines = (net.lines.s_nom == 0).sum()
            if zero_lines > 0:
                warnings.append(f"Lines with s_nom=0: {zero_lines}/{len(net.lines)}")
        if len(net.transformers) > 0:
            zero_xfmr = (net.transformers.s_nom == 0).sum()
            if zero_xfmr > 0:
                warnings.append(f"Transformers with s_nom=0: {zero_xfmr}/{len(net.transformers)}")

        # Slack bus
        if "control" in net.generators.columns:
            n_slack = (net.generators.control == "Slack").sum()
            if n_slack == 0:
                warnings.append("No slack generator found")
            else:
                print(f"  Slack generators: {n_slack}")

        # Generator cost
        if "marginal_cost" in net.generators.columns:
            if net.generators.marginal_cost.abs().sum() == 0:
                warnings.append("marginal_cost all zero (gencost not imported by PyPSA)")

        if warnings:
            print("  Data quality warnings:")
            for w in warnings:
                print(f"    - {w}")
