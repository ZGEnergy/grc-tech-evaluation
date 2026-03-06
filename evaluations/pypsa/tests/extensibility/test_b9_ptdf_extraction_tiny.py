"""B-9 (ptdf_extraction) — Compute PTDF matrix for IEEE 39-bus (TINY).

Pass condition: Use sub_network.calculate_PTDF().
Verify dimensions (branches x buses), verify flow predictions match DCPF.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case39.m")


def load_network(filepath: str | Path) -> pypsa.Network:
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    return n


def run() -> dict:
    """Execute B-9 PTDF extraction test."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network(CASE_FILE)

        # Run DCPF first to get reference flows
        n.lpf()
        ref_line_flows = n.lines_t.p0.iloc[0].copy()
        ref_xfmr_flows = n.transformers_t.p0.iloc[0].copy()

        t0 = time.perf_counter()

        # Determine network topology (required before PTDF calculation)
        n.determine_network_topology()

        # Get the sub_network object
        sub_networks = list(n.sub_networks.index)
        details["n_sub_networks"] = len(sub_networks)

        # Calculate PTDF for the first (main) sub_network
        sub = n.sub_networks.obj[sub_networks[0]]
        sub.calculate_PTDF()

        ptdf = sub.PTDF
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["ptdf_shape"] = list(ptdf.shape)
        details["ptdf_type"] = type(ptdf).__name__
        details["ptdf_dtype"] = str(ptdf.dtype)
        details["ptdf_density"] = round(float(np.count_nonzero(ptdf) / ptdf.size), 4)
        details["ptdf_range"] = [round(float(ptdf.min()), 6), round(float(ptdf.max()), 6)]

        # Expected dimensions: branches x buses (within sub_network)
        # sub_network contains a subset of buses and branches
        sn_buses = sub.buses_i()
        sn_branches = sub.branches_i()
        details["sub_network_buses"] = len(sn_buses)
        details["sub_network_branches"] = len(sn_branches)
        details["expected_rows"] = len(sn_branches)
        details["expected_cols"] = len(sn_buses)

        # Verify dimensions
        assert ptdf.shape[0] == len(sn_branches), (
            f"PTDF rows {ptdf.shape[0]} != branches {len(sn_branches)}"
        )
        assert ptdf.shape[1] == len(sn_buses), f"PTDF cols {ptdf.shape[1]} != buses {len(sn_buses)}"
        details["dimensions_correct"] = True

        # Verify flow predictions match DCPF
        # Flow = PTDF * P_injection
        # PTDF columns are ordered by sub.buses_o (slack bus first, then non-slack).
        # The slack bus column is all zeros (flows are relative to slack).
        bus_injection = n.buses_t.p.iloc[0]
        buses_o = list(sub.buses_o)  # internal bus ordering used by PTDF
        details["slack_bus"] = sub.slack_bus
        details["ptdf_bus_ordering"] = "sub.buses_o (slack first, then non-slack)"
        details["slack_column_all_zeros"] = bool(np.abs(ptdf[:, 0]).sum() < 1e-10)

        # Map bus injections to buses_o order
        p_inj = np.array([bus_injection[b] for b in buses_o])

        # Predict flows using PTDF
        predicted_flows = ptdf @ p_inj

        # Compare with actual DCPF flows
        # Get actual flows for branches in sub_network, in same order
        actual_flows = []
        branch_names = []
        for comp, name in sn_branches:
            if comp == "Line":
                actual_flows.append(ref_line_flows[name])
            elif comp == "Transformer":
                actual_flows.append(ref_xfmr_flows[name])
            branch_names.append(f"{comp}:{name}")

        actual_flows = np.array(actual_flows)

        # Compute prediction error
        max_error = float(np.max(np.abs(predicted_flows - actual_flows)))
        mean_error = float(np.mean(np.abs(predicted_flows - actual_flows)))
        details["prediction_max_error_mw"] = round(max_error, 8)
        details["prediction_mean_error_mw"] = round(mean_error, 8)
        details["prediction_within_tolerance"] = max_error < 1e-4  # very tight for DCPF

        # Sample of predictions vs actuals
        details["flow_comparison_sample"] = []
        for i in range(min(5, len(actual_flows))):
            details["flow_comparison_sample"].append(
                {
                    "branch": branch_names[i],
                    "actual_mw": round(actual_flows[i], 4),
                    "predicted_mw": round(predicted_flows[i], 4),
                    "error_mw": round(abs(predicted_flows[i] - actual_flows[i]), 8),
                }
            )

        details["api_method"] = (
            "n.determine_network_topology() -> "
            "n.sub_networks.obj['0'].calculate_PTDF() -> sub.PTDF (numpy array)"
        )
        details["loc"] = 5

        assert details["prediction_within_tolerance"], (
            f"PTDF predictions don't match DCPF (max error: {max_error})"
        )
        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "B-9",
        "slug": "ptdf_extraction",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
