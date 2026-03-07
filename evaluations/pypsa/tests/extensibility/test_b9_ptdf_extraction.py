"""
Test B-9: Compute PTDF matrix for TINY (39-bus), verify dimensions and flow prediction

Dimension: extensibility
Network: TINY (case39)
Pass condition: PTDF matrix accessible via native API, internal matrix extraction, or
    unit-injection computation. Flow predictions match DCPF results within numerical
    tolerance (1e-6).
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")


def _load_network(case_path: str):
    """Load MATPOWER .m file into PyPSA Network via matpowercaseframes."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute PTDF extraction and verification.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    try:
        # 1. Load network (not timed)
        n = _load_network(network_file)

        # 2. Run DCPF to get reference flows
        n.lpf()

        n_lines = len(n.lines)
        n_transformers = len(n.transformers)
        n_branches = n_lines + n_transformers
        n_buses = len(n.buses)

        # 3. Extract PTDF matrix (timed)
        # PyPSA exposes SubNetwork.calculate_PTDF() as a native public API method.
        # It computes PTDF = H @ B^-1, stored as sn.PTDF (dense numpy array).
        n.determine_network_topology()
        sn = n.sub_networks.obj.iloc[0]

        start = time.perf_counter()
        sn.calculate_PTDF()
        elapsed_ptdf = time.perf_counter() - start

        ptdf = sn.PTDF  # numpy ndarray
        ptdf_shape = ptdf.shape

        # 4. Verify dimensions: should be (n_branches x n_buses)
        expected_shape = (n_branches, n_buses)
        shape_correct = ptdf_shape == expected_shape

        # 5. Compute predicted flows = PTDF @ nodal_injections
        # CRITICAL: The PTDF column ordering is [slack_bus] + list(pvpqs),
        # NOT the same as buses_i(). The slack bus column is at index 0,
        # followed by all PV/PQ buses in the pvpqs ordering.
        slack_bus = str(sn.slack_bus)
        bus_order = [slack_bus] + list(sn.pvpqs)

        # Build injection vector in PTDF column order
        bus_p = n.buses_t.p.iloc[0]
        injections = np.array([bus_p[bus] for bus in bus_order])

        # Compute predicted flows (PTDF operates on MW injections directly)
        predicted_flows = ptdf @ injections

        # 6. Get DCPF flows in the same branch ordering as PTDF rows
        # PTDF rows follow sn.branches_i() ordering
        sn_branches = list(sn.branches_i())
        dcpf_flows_ordered = []
        for comp_type, branch_name in sn_branches:
            if comp_type == "Line":
                flow = float(n.lines_t.p0.iloc[0][branch_name])
            elif comp_type == "Transformer":
                flow = float(n.transformers_t.p0.iloc[0][branch_name])
            else:
                flow = 0.0
            dcpf_flows_ordered.append(flow)
        dcpf_flows_ordered = np.array(dcpf_flows_ordered)

        elapsed_total = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed_total

        # 7. Compare predicted vs DCPF flows
        flow_diff = np.abs(predicted_flows - dcpf_flows_ordered)
        max_diff = float(flow_diff.max())
        mean_diff = float(flow_diff.mean())
        flows_match = max_diff < 1e-6

        # 8. Additional PTDF properties check
        # Slack bus column should be all zeros (reference bus)
        slack_col_max = float(np.abs(ptdf[:, 0]).max())

        # Row sums should be zero (for PTDF with slack at reference)
        # Actually, for DC PTDF, row sums = 0 only if slack column is zero
        row_sums = ptdf.sum(axis=1)
        max_row_sum = float(np.abs(row_sums).max())

        # 9. Pass condition
        pass_condition_met = shape_correct and flows_match

        if pass_condition_met:
            results["status"] = "pass"

        # Build branch-by-branch comparison for top mismatches
        flow_comparison = []
        for i, (comp_type, branch_name) in enumerate(sn_branches):
            flow_comparison.append(
                {
                    "branch": f"{comp_type}-{branch_name}",
                    "dcpf_flow_MW": float(dcpf_flows_ordered[i]),
                    "ptdf_predicted_MW": float(predicted_flows[i]),
                    "abs_diff": float(flow_diff[i]),
                }
            )
        # Sort by absolute difference descending
        flow_comparison.sort(key=lambda x: x["abs_diff"], reverse=True)

        results["details"] = {
            "ptdf_shape": list(ptdf_shape),
            "expected_shape": list(expected_shape),
            "shape_correct": shape_correct,
            "n_buses": n_buses,
            "n_lines": n_lines,
            "n_transformers": n_transformers,
            "n_branches": n_branches,
            "ptdf_computation_seconds": elapsed_ptdf,
            "api_method": "SubNetwork.calculate_PTDF() -> sn.PTDF (numpy ndarray)",
            "api_type": "native public API",
            "column_ordering": "PTDF columns are [slack_bus] + pvpqs (not buses_i())",
            "max_flow_diff": max_diff,
            "mean_flow_diff": mean_diff,
            "flows_match_1e6": flows_match,
            "tolerance": 1e-6,
            "ptdf_row_sum_max": max_row_sum,
            "slack_bus": slack_bus,
            "slack_col_max_abs": slack_col_max,
            "top_5_mismatches": flow_comparison[:5],
            "top_5_flows": sorted(
                flow_comparison,
                key=lambda x: abs(x["dcpf_flow_MW"]),
                reverse=True,
            )[:5],
        }

        if not flows_match:
            results["workarounds"].append(
                "PTDF column ordering is [slack_bus] + pvpqs, not buses_i(). "
                "Injection vector must be built in this order for correct flow prediction."
            )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
