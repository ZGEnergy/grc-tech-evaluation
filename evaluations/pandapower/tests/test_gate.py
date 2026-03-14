"""Gate tests for pandapower: G-1 (TINY), G-2 (SMALL), G-3 (MEDIUM).

Each test loads a MATPOWER .m file via pandapower's from_mpc converter,
verifies bus/branch/generator counts, and runs post-import data quality audits.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

# Reference counts derived from the .m files
NETWORKS = {
    "TINY": {
        "file": "case39.m",
        "buses": 39,
        "branches": 46,
        "generators": 10,
    },
    "SMALL": {
        "file": "case_ACTIVSg2000.m",
        "buses": 2000,
        "branches": 3206,
        "generators": 544,
    },
    "MEDIUM": {
        "file": "case_ACTIVSg10k.m",
        "buses": 10000,
        "branches": 12706,
        "generators": 2485,
    },
}


def _load_network(data_dir: Path, tier: str):
    """Load a MATPOWER case file and return (net, load_time_s, warnings)."""
    from pandapower.converter.matpower.from_mpc import from_mpc

    case_file = str(data_dir / NETWORKS[tier]["file"])
    t0 = time.perf_counter()
    net = from_mpc(case_file)
    load_time = time.perf_counter() - t0
    return net, load_time


def _count_elements(net):
    """Return (bus_count, branch_count, gen_count) from a pandapower network.

    pandapower's from_mpc converter maps MATPOWER branches to four element types:
      - line: standard transmission lines
      - trafo: two-winding transformers (branches with tap ratio != 0/1 AND different voltage levels)
      - trafo3w: three-winding transformers (rare)
      - impedance: branches with tap ratio != 0/1 connecting same voltage levels
    Similarly, generators map to:
      - gen: dispatchable generators
      - ext_grid: slack/reference bus generator
      - sgen: static generators (negative loads in MATPOWER)
    """
    bus_count = len(net.bus)
    branch_count = len(net.line) + len(net.trafo) + len(net.trafo3w) + len(net.impedance)
    gen_count = len(net.gen) + len(net.ext_grid) + len(net.sgen)
    return bus_count, branch_count, gen_count


def _audit_data_quality(net):
    """Post-import data quality audit. Returns dict of findings."""
    findings = {}

    # Bus voltage magnitude checks (vm_pu)
    if "vm_pu" in net.bus.columns:
        vm = net.bus["vm_pu"]
        findings["bus_vm_nan"] = int(vm.isna().sum())
        findings["bus_vm_inf"] = int(np.isinf(vm.astype(float)).sum())
    else:
        findings["bus_vm_nan"] = "column missing"

    # Bus voltage angle checks (va_degree)
    if "va_degree" in net.bus.columns:
        va = net.bus["va_degree"]
        findings["bus_va_nan"] = int(va.isna().sum())
    else:
        findings["bus_va_nan"] = "column missing"

    # Line rating checks (max_i_ka)
    if "max_i_ka" in net.line.columns:
        ratings = net.line["max_i_ka"]
        findings["line_rating_nan"] = int(ratings.isna().sum())
        findings["line_rating_inf"] = int(np.isinf(ratings.astype(float)).sum())
        findings["line_rating_zero"] = int((ratings == 0).sum())
    else:
        findings["line_rating_present"] = False

    # Transformer rating checks
    if len(net.trafo) > 0:
        if "sn_mva" in net.trafo.columns:
            t_ratings = net.trafo["sn_mva"]
            findings["trafo_rating_nan"] = int(t_ratings.isna().sum())
        else:
            findings["trafo_rating_present"] = False

    # Generator limit checks (min_p_mw, max_p_mw)
    for gen_table_name in ["gen", "ext_grid"]:
        gen_table = getattr(net, gen_table_name)
        if len(gen_table) > 0:
            for col in ["min_p_mw", "max_p_mw"]:
                if col in gen_table.columns:
                    vals = gen_table[col]
                    findings[f"{gen_table_name}_{col}_nan"] = int(vals.isna().sum())
                    findings[f"{gen_table_name}_{col}_inf"] = int(
                        np.isinf(vals.astype(float)).sum()
                    )

    # Generator cost data (poly_cost table)
    findings["poly_cost_rows"] = len(net.poly_cost) if hasattr(net, "poly_cost") else 0
    findings["pwl_cost_rows"] = len(net.pwl_cost) if hasattr(net, "pwl_cost") else 0
    findings["cost_data_present"] = findings["poly_cost_rows"] > 0 or findings["pwl_cost_rows"] > 0

    # Slack/reference bus identification
    findings["ext_grid_count"] = len(net.ext_grid)
    findings["slack_identified"] = len(net.ext_grid) > 0

    return findings


class TestGate:
    """Gate tests verifying pandapower can import and parse MATPOWER data files."""

    def test_import(self) -> None:
        """pandapower core library can be imported."""
        import pandapower as pp

        assert hasattr(pp, "__version__")
        assert isinstance(pp.__version__, str)

    @pytest.mark.parametrize(
        "tier",
        ["TINY", "SMALL", "MEDIUM"],
        ids=["G-1_TINY", "G-2_SMALL", "G-3_MEDIUM"],
    )
    def test_gate_ingest(self, data_dir: Path, tier: str) -> None:
        """Gate test: load MATPOWER case, verify counts, run data quality audit."""
        ref = NETWORKS[tier]

        # Load
        net, load_time = _load_network(data_dir, tier)
        bus_count, branch_count, gen_count = _count_elements(net)

        # Report counts
        print(f"\n{'=' * 60}")
        print(f"Gate test: {tier}")
        print(f"File: {ref['file']}")
        print(f"Load time: {load_time:.3f}s")
        print(
            f"Expected: {ref['buses']} buses / {ref['branches']} branches / {ref['generators']} gens"
        )
        print(f"Actual:   {bus_count} buses / {branch_count} branches / {gen_count} gens")
        print(
            f"  branches: line={len(net.line)}, trafo={len(net.trafo)}, trafo3w={len(net.trafo3w)}, impedance={len(net.impedance)}"
        )
        print(f"  gens: gen={len(net.gen)}, ext_grid={len(net.ext_grid)}, sgen={len(net.sgen)}")

        # Data quality audit
        audit = _audit_data_quality(net)
        print("\nData quality audit:")
        for k, v in audit.items():
            print(f"  {k}: {v}")
        print(f"{'=' * 60}")

        # Assertions
        assert bus_count == ref["buses"], (
            f"Bus count mismatch: expected {ref['buses']}, got {bus_count}"
        )
        assert branch_count == ref["branches"], (
            f"Branch count mismatch: expected {ref['branches']}, got {branch_count}"
        )
        assert gen_count == ref["generators"], (
            f"Generator count mismatch: expected {ref['generators']}, got {gen_count}"
        )

        # Data quality assertions (warnings, not hard failures for gate)
        assert audit["slack_identified"], "No slack/reference bus identified"
