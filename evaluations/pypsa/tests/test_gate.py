"""Gate tests for PyPSA: network ingestion at TINY/SMALL/MEDIUM tiers.

Protocol v4 gate tests G-1, G-2, G-3.
Conversion pipeline: matpowercaseframes -> PYPOWER PPC dict -> pypsa.Network.import_from_pypower_ppc()
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

# Reference counts extracted from the .m files
REFERENCE = {
    "G-1": {
        "tier": "TINY",
        "file": "case39.m",
        "buses": 39,
        "branches": 46,
        "generators": 10,
    },
    "G-2": {
        "tier": "SMALL",
        "file": "case_ACTIVSg2000.m",
        "buses": 2000,
        "branches": 3206,
        "generators": 544,
    },
    "G-3": {
        "tier": "MEDIUM",
        "file": "case_ACTIVSg10k.m",
        "buses": 10000,
        "branches": 12706,
        "generators": 2485,
    },
}


def _load_network(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    import pypsa
    from matpowercaseframes import CaseFrames

    t0 = time.perf_counter()
    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    # Include gencost if available
    try:
        ppc["gencost"] = cf.gencost.values
    except Exception:
        pass

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    elapsed = time.perf_counter() - t0
    return net, elapsed, cf


def _audit_network(net, ref: dict) -> dict:
    """Post-import data quality audit. Returns dict of findings."""
    findings = {}

    # Bus voltage magnitudes
    if "v_nom" in net.buses.columns:
        nan_vnom = net.buses["v_nom"].isna().sum()
        inf_vnom = np.isinf(net.buses["v_nom"]).sum()
        findings["bus_v_nom_nan"] = int(nan_vnom)
        findings["bus_v_nom_inf"] = int(inf_vnom)

    # Line ratings (s_nom)
    if len(net.lines) > 0 and "s_nom" in net.lines.columns:
        nan_snom = net.lines["s_nom"].isna().sum()
        zero_snom = (net.lines["s_nom"] == 0).sum()
        findings["line_s_nom_nan"] = int(nan_snom)
        findings["line_s_nom_zero"] = int(zero_snom)

    # Transformer ratings
    if len(net.transformers) > 0 and "s_nom" in net.transformers.columns:
        nan_tsnom = net.transformers["s_nom"].isna().sum()
        zero_tsnom = (net.transformers["s_nom"] == 0).sum()
        findings["transformer_s_nom_nan"] = int(nan_tsnom)
        findings["transformer_s_nom_zero"] = int(zero_tsnom)

    # Generator limits
    if len(net.generators) > 0:
        for col in ["p_nom", "p_min_pu", "p_max_pu"]:
            if col in net.generators.columns:
                nan_count = net.generators[col].isna().sum()
                findings[f"gen_{col}_nan"] = int(nan_count)

    # Generator cost data (marginal_cost)
    if len(net.generators) > 0 and "marginal_cost" in net.generators.columns:
        nan_mc = net.generators["marginal_cost"].isna().sum()
        zero_mc = (net.generators["marginal_cost"] == 0).sum()
        findings["gen_marginal_cost_nan"] = int(nan_mc)
        findings["gen_marginal_cost_zero"] = int(zero_mc)
    else:
        findings["gen_marginal_cost_missing"] = True

    # Slack bus
    slack_buses = net.buses[net.buses.get("control", net.buses.get("carrier", "")) == "Slack"]
    if len(slack_buses) == 0:
        # Check generators for slack
        if len(net.generators) > 0 and "control" in net.generators.columns:
            slack_gens = net.generators[net.generators["control"] == "Slack"]
            findings["slack_generators"] = len(slack_gens)
        else:
            findings["slack_bus_identified"] = False
    else:
        findings["slack_bus_identified"] = True

    return findings


class TestGate:
    """Gate tests G-1, G-2, G-3: MATPOWER network ingestion at three tiers."""

    @pytest.mark.parametrize(
        "test_id",
        ["G-1", "G-2", "G-3"],
        ids=["G-1_TINY_case39", "G-2_SMALL_ACTIVSg2000", "G-3_MEDIUM_ACTIVSg10k"],
    )
    def test_gate_ingestion(self, data_dir: Path, test_id: str) -> None:
        """Load MATPOWER case, verify counts, run data quality audit."""
        ref = REFERENCE[test_id]
        case_path = str(data_dir / ref["file"])

        # Load network
        net, elapsed, cf = _load_network(case_path)

        # Count components
        actual_buses = len(net.buses)
        actual_branches = len(net.lines) + len(net.transformers)
        actual_generators = len(net.generators)

        # Print details for result file generation
        print(f"\n--- {test_id} ({ref['tier']}) ---")
        print(f"File: {ref['file']}")
        print(f"Load time: {elapsed:.3f}s")
        print(
            f"Expected: buses={ref['buses']}, branches={ref['branches']}, gens={ref['generators']}"
        )
        print(
            f"Actual:   buses={actual_buses}, branches={actual_branches}, gens={actual_generators}"
        )
        print(f"  Lines: {len(net.lines)}, Transformers: {len(net.transformers)}")

        # Audit
        audit = _audit_network(net, ref)
        print(f"Audit: {audit}")

        # Assert counts
        assert actual_buses == ref["buses"], (
            f"Bus count mismatch: expected {ref['buses']}, got {actual_buses}"
        )
        assert actual_branches == ref["branches"], (
            f"Branch count mismatch: expected {ref['branches']}, got {actual_branches}"
        )
        assert actual_generators == ref["generators"], (
            f"Generator count mismatch: expected {ref['generators']}, got {actual_generators}"
        )
