"""
Test C-9: PTDF Matrix Computation Scale Test

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k)
Pass condition: PTDF matrix computed successfully. Wall-clock, memory, and matrix
    dimensions recorded. May OOM on 10k-bus.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import json
import math
import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

TIMEOUT_SECONDS = 600


def _load_network(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
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

    # Fix zero impedance branches (causes singular matrix)
    zero_x_lines = net.lines["x"] == 0
    if zero_x_lines.any():
        net.lines.loc[zero_x_lines, "x"] = 0.0001

    zero_x_xfmr = net.transformers["x"] == 0
    if zero_x_xfmr.any():
        net.transformers.loc[zero_x_xfmr, "x"] = 0.0001

    return net


def _get_peak_memory_mb():
    """Get peak memory usage in MB using resource module."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024.0
    except Exception:
        return None


def run(network_file: str = NETWORK_FILE) -> dict:
    """Compute PTDF matrix on 10k-bus network."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pypsa

        mem_before = _get_peak_memory_mb()

        # 1. Load network
        n = _load_network(network_file)

        n_lines = len(n.lines)
        n_transformers = len(n.transformers)
        n_branches = n_lines + n_transformers
        n_buses = len(n.buses)

        network_stats = {
            "n_buses": n_buses,
            "n_lines": n_lines,
            "n_transformers": n_transformers,
            "n_branches": n_branches,
        }

        # Estimate PTDF matrix size
        ptdf_size_bytes = n_branches * n_buses * 8  # float64
        ptdf_size_mb = ptdf_size_bytes / (1024 * 1024)
        results["details"]["estimated_ptdf_size_mb"] = ptdf_size_mb

        # 2. Run DCPF to establish topology
        n.lpf()

        # 3. Determine network topology
        n.determine_network_topology()

        # Check if there are multiple sub-networks
        n_sub_networks = len(n.sub_networks)
        results["details"]["n_sub_networks"] = n_sub_networks

        # 4. Compute PTDF for largest sub-network
        sn = n.sub_networks.obj.iloc[0]

        ptdf_start = time.perf_counter()
        sn.calculate_PTDF()
        ptdf_elapsed = time.perf_counter() - ptdf_start

        ptdf = sn.PTDF
        ptdf_shape = ptdf.shape

        mem_after_ptdf = _get_peak_memory_mb()

        # 5. Verify dimensions
        sn_buses = len(list(sn.buses_i()))
        sn_branches_list = list(sn.branches_i())
        sn_n_branches = len(sn_branches_list)
        expected_shape = (sn_n_branches, sn_buses)
        shape_correct = ptdf_shape == expected_shape

        # 6. Verify flow prediction accuracy
        slack_bus = str(sn.slack_bus)
        bus_order = [slack_bus] + list(sn.pvpqs)

        bus_p = n.buses_t.p.iloc[0]
        injections = np.array([bus_p[bus] for bus in bus_order])
        predicted_flows = ptdf @ injections

        dcpf_flows_ordered = []
        for comp_type, branch_name in sn_branches_list:
            if comp_type == "Line":
                flow = float(n.lines_t.p0.iloc[0][branch_name])
            elif comp_type == "Transformer":
                flow = float(n.transformers_t.p0.iloc[0][branch_name])
            else:
                flow = 0.0
            dcpf_flows_ordered.append(flow)
        dcpf_flows_ordered = np.array(dcpf_flows_ordered)

        flow_diff = np.abs(predicted_flows - dcpf_flows_ordered)
        max_diff = float(flow_diff.max())
        mean_diff = float(flow_diff.mean())
        flows_match = max_diff < 1e-4  # Relaxed tolerance for large network

        # 7. PTDF properties
        slack_col_max = float(np.abs(ptdf[:, 0]).max())
        row_sums = ptdf.sum(axis=1)
        max_row_sum = float(np.abs(row_sums).max())

        # Actual memory used by PTDF array
        ptdf_actual_mb = ptdf.nbytes / (1024 * 1024)

        total_elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = total_elapsed

        results["details"] = {
            "ptdf_shape": list(ptdf_shape),
            "expected_shape": list(expected_shape),
            "shape_correct": shape_correct,
            "network": network_stats,
            "sub_network_buses": sn_buses,
            "sub_network_branches": sn_n_branches,
            "n_sub_networks": n_sub_networks,
            "ptdf_computation_seconds": ptdf_elapsed,
            "ptdf_actual_size_mb": ptdf_actual_mb,
            "estimated_ptdf_size_mb": ptdf_size_mb,
            "api_method": "SubNetwork.calculate_PTDF() -> sn.PTDF (numpy ndarray)",
            "max_flow_diff": max_diff,
            "mean_flow_diff": mean_diff,
            "flows_match": flows_match,
            "tolerance": 1e-4,
            "slack_bus": slack_bus,
            "slack_col_max_abs": slack_col_max,
            "max_row_sum_abs": max_row_sum,
            "peak_memory_mb": mem_after_ptdf,
            "mem_before_mb": mem_before,
            "pypsa_version": pypsa.__version__,
        }

        if shape_correct and flows_match:
            results["status"] = "pass"
        elif shape_correct:
            results["status"] = "qualified_pass"
            results["workarounds"].append(
                f"PTDF flow prediction max diff {max_diff:.6f} exceeds tolerance 1e-4"
            )

    except MemoryError as e:
        results["errors"].append(f"MemoryError: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["details"]["note"] = (
            f"PTDF matrix for {n_buses} buses x {n_branches} branches = "
            f"{ptdf_size_mb:.1f} MB exceeded available memory"
        )
        results["wall_clock_seconds"] = time.perf_counter() - start
    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":

    def _json_safe(obj):
        if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
            return str(obj)
        return str(obj)

    result = run()
    print(json.dumps(result, indent=2, default=_json_safe))
