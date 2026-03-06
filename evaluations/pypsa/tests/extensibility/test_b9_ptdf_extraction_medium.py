"""B-9 (ptdf_extraction) -- Compute PTDF matrix for ACTIVSg10k (MEDIUM).

IMPORTANT: use sub.buses_o for column ordering. Fix zero-impedance branches.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg10k.m")


def load_network(filepath):
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
    # Fix zero-impedance branches that cause singular B matrix
    zero_x_lines = n.lines.x == 0
    if zero_x_lines.any():
        n.lines.loc[zero_x_lines, "x"] = 1e-4
    zero_x_xfmrs = n.transformers.x == 0
    if zero_x_xfmrs.any():
        n.transformers.loc[zero_x_xfmrs, "x"] = 1e-4
    return n, int(zero_x_lines.sum()), int(zero_x_xfmrs.sum())


def run():
    errors = []
    workarounds = []
    details = {}
    try:
        n, zl, zx = load_network(CASE_FILE)
        details["buses"] = len(n.buses)
        details["lines"] = len(n.lines)
        details["transformers"] = len(n.transformers)
        details["zero_impedance_lines_fixed"] = zl
        details["zero_impedance_transformers_fixed"] = zx
        if zl > 0 or zx > 0:
            workarounds.append(
                {
                    "type": "stable",
                    "description": f"Fixed {zl} lines and {zx} transformers with zero impedance (set x=1e-4) to avoid singular B matrix in PTDF calculation.",
                }
            )

        n.lpf()
        ref_line_flows = n.lines_t.p0.iloc[0].copy()
        ref_xfmr_flows = n.transformers_t.p0.iloc[0].copy()

        t0 = time.perf_counter()
        n.determine_network_topology()
        sub_networks = list(n.sub_networks.index)
        details["n_sub_networks"] = len(sub_networks)
        sub = n.sub_networks.obj[sub_networks[0]]
        sub.calculate_PTDF()
        ptdf = sub.PTDF
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["ptdf_shape"] = list(ptdf.shape)
        details["ptdf_type"] = type(ptdf).__name__
        details["ptdf_dtype"] = str(ptdf.dtype)
        details["ptdf_memory_mb"] = round(ptdf.nbytes / 1024 / 1024, 2)
        details["ptdf_density"] = round(float(np.count_nonzero(ptdf) / ptdf.size), 4)
        details["ptdf_range"] = [round(float(ptdf.min()), 6), round(float(ptdf.max()), 6)]

        sn_buses = sub.buses_i()
        sn_branches = sub.branches_i()
        details["sub_network_buses"] = len(sn_buses)
        details["sub_network_branches"] = len(sn_branches)

        assert ptdf.shape[0] == len(sn_branches), (
            f"PTDF rows {ptdf.shape[0]} != branches {len(sn_branches)}"
        )
        assert ptdf.shape[1] == len(sn_buses), f"PTDF cols {ptdf.shape[1]} != buses {len(sn_buses)}"
        details["dimensions_correct"] = True

        bus_injection = n.buses_t.p.iloc[0]
        buses_o = list(sub.buses_o)
        details["slack_bus"] = sub.slack_bus
        p_inj = np.array([bus_injection[b] for b in buses_o])
        predicted_flows = ptdf @ p_inj

        actual_flows = []
        branch_names = []
        for comp, name in sn_branches:
            if comp == "Line":
                actual_flows.append(ref_line_flows[name])
            elif comp == "Transformer":
                actual_flows.append(ref_xfmr_flows[name])
            branch_names.append(f"{comp}:{name}")
        actual_flows = np.array(actual_flows)

        max_error = float(np.max(np.abs(predicted_flows - actual_flows)))
        mean_error = float(np.mean(np.abs(predicted_flows - actual_flows)))
        details["prediction_max_error_mw"] = round(max_error, 6)
        details["prediction_mean_error_mw"] = round(mean_error, 6)
        details["prediction_within_tolerance"] = max_error < 0.1

        details["flow_comparison_sample"] = []
        for i in range(min(5, len(actual_flows))):
            details["flow_comparison_sample"].append(
                {
                    "branch": branch_names[i],
                    "actual_mw": round(actual_flows[i], 4),
                    "predicted_mw": round(predicted_flows[i], 4),
                    "error_mw": round(abs(predicted_flows[i] - actual_flows[i]), 6),
                }
            )

        details["api_method"] = "n.determine_network_topology() -> sub.calculate_PTDF() -> sub.PTDF"
        details["loc"] = 5
        status = "PASS"
    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
    return {
        "test_id": "B-9",
        "slug": "ptdf_extraction",
        "tier": "MEDIUM",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
