"""
Test B-9: Compute PTDF matrix for TINY and verify against DCPF flows.

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: PTDF accessible via native API. Flow predictions match DCPF results
    within 1e-6 tolerance.
Tool: gridcal (VeraGridEngine) 5.6.28
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute B-9 PTDF extraction test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        # 1. Load network
        grid = load_gridcal(network_file)
        buses = grid.get_buses()
        branches = grid.get_branches()
        n_buses = len(buses)
        n_branches = len(branches)
        branch_names = [b.name for b in branches]

        results["details"]["bus_count"] = n_buses
        results["details"]["branch_count"] = n_branches

        # 2. Compute PTDF via LinearAnalysis (native API)
        t_ptdf_start = time.perf_counter()
        la_results = vge.linear_power_flow(grid)
        t_ptdf_end = time.perf_counter()

        ptdf = la_results.PTDF
        lodf = la_results.LODF
        results["details"]["ptdf_shape"] = list(ptdf.shape)
        results["details"]["lodf_shape"] = list(lodf.shape)
        results["details"]["ptdf_compute_seconds"] = round(t_ptdf_end - t_ptdf_start, 6)

        # PTDF matrix properties
        results["details"]["ptdf_max"] = float(np.max(np.abs(ptdf)))
        results["details"]["ptdf_nonzero_pct"] = round(
            float(np.count_nonzero(ptdf)) / ptdf.size * 100, 1
        )

        # 3. Run DCPF for comparison
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        pf_results = vge.power_flow(grid, options=pf_opts)

        assert pf_results.converged, "DCPF did not converge"
        results["details"]["dcpf_converged"] = True

        dcpf_flows = np.real(pf_results.Sf)
        results["details"]["dcpf_flows_sample"] = {
            branch_names[i]: round(float(dcpf_flows[i]), 6) for i in range(min(10, n_branches))
        }

        # 4. Predict flows using PTDF: flow = PTDF @ Pinj
        Pinj = np.real(la_results.Sbus)
        results["details"]["pinj_total_mw"] = round(float(np.sum(Pinj)), 6)

        ptdf_predicted_flows = ptdf @ Pinj

        # 5. Check for phase-shifting transformers
        phase_shifter_indices = []
        for i, br in enumerate(branches):
            # Check if branch has a nonzero phase shift angle
            shift = getattr(br, "tap_phase", 0.0) or getattr(br, "angle", 0.0) or 0.0
            if abs(shift) > 1e-6:
                phase_shifter_indices.append(i)

        results["details"]["phase_shifter_count"] = len(phase_shifter_indices)
        if phase_shifter_indices:
            results["details"]["phase_shifter_indices"] = phase_shifter_indices

        # 6. Compare PTDF-predicted flows vs DCPF flows
        abs_diff = np.abs(ptdf_predicted_flows - dcpf_flows)

        # If phase shifters exist, compute stats both with and without them
        if phase_shifter_indices:
            mask = np.ones(n_branches, dtype=bool)
            mask[phase_shifter_indices] = False

            results["details"]["max_abs_diff_all"] = float(np.max(abs_diff))
            results["details"]["mean_abs_diff_all"] = float(np.mean(abs_diff))
            results["details"]["max_abs_diff_excl_ps"] = float(np.max(abs_diff[mask]))
            results["details"]["mean_abs_diff_excl_ps"] = float(np.mean(abs_diff[mask]))
            max_diff_for_pass = float(np.max(abs_diff[mask]))
        else:
            max_diff_for_pass = float(np.max(abs_diff))

        results["details"]["max_abs_diff"] = float(np.max(abs_diff))
        results["details"]["mean_abs_diff"] = float(np.mean(abs_diff))

        # Per-branch comparison (first 10)
        results["details"]["branch_comparison"] = {
            branch_names[i]: {
                "dcpf_flow_mw": round(float(dcpf_flows[i]), 6),
                "ptdf_flow_mw": round(float(ptdf_predicted_flows[i]), 6),
                "abs_diff": round(float(abs_diff[i]), 10),
            }
            for i in range(min(10, n_branches))
        }

        # 7. Also verify PTDF internal consistency: la_results.Sf should match PTDF @ Pinj
        la_flows = np.real(la_results.Sf)
        internal_diff = float(np.max(np.abs(la_flows - ptdf_predicted_flows)))
        results["details"]["internal_consistency_diff"] = internal_diff

        # Also verify la_results.Sf matches DCPF Sf
        la_vs_dcpf_diff = float(np.max(np.abs(la_flows - dcpf_flows)))
        results["details"]["la_vs_dcpf_max_diff"] = la_vs_dcpf_diff

        # 8. Check pass condition: PTDF accessible, flows match within 1e-6
        tolerance = 1e-6
        pass_checks = {
            "ptdf_accessible_via_native_api": True,
            "ptdf_shape_correct": ptdf.shape == (n_branches, n_buses),
            "dcpf_converged": bool(pf_results.converged),
            "flow_match_within_tolerance": max_diff_for_pass < tolerance,
        }
        results["details"]["pass_checks"] = pass_checks
        results["details"]["tolerance"] = tolerance
        results["details"]["max_diff_for_pass"] = max_diff_for_pass

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
