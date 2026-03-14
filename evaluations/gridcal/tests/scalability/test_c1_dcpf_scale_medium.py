"""
Test C-1: DCPF on MEDIUM — wall-clock time and peak memory.

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: DCPF solves on MEDIUM.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: Linear (direct, no optimizer)
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute C-1 DCPF scale test on MEDIUM and return structured results."""
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
        n_buses = grid.get_bus_number()
        n_branches = grid.get_branch_number()
        n_gens = len(grid.get_generators())
        n_loads = len(grid.get_loads())

        results["details"]["bus_count"] = n_buses
        results["details"]["branch_count"] = n_branches
        results["details"]["gen_count"] = n_gens
        results["details"]["load_count"] = n_loads

        # 2. Configure DC power flow
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)

        # 3. Execute DCPF with timing and memory measurement
        tracemalloc.start()
        solve_start = time.perf_counter()
        pf_results = vge.power_flow(grid, options=pf_opts)
        solve_elapsed = time.perf_counter() - solve_start
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_wall_clock_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)

        # 4. Extract results
        converged = bool(pf_results.converged)
        results["details"]["converged"] = converged

        if not converged:
            results["errors"].append("DCPF did not converge on MEDIUM network")
            return results

        # Voltage angles
        voltage = pf_results.voltage
        angles_rad = np.angle(voltage)
        angles_deg = np.degrees(angles_rad)
        magnitudes = np.abs(voltage)

        results["details"]["has_nonzero_angles"] = bool(np.any(angles_deg != 0.0))
        results["details"]["max_angle_deg"] = float(np.max(np.abs(angles_deg)))
        results["details"]["mean_angle_deg"] = float(np.mean(np.abs(angles_deg)))

        # Branch flows
        sf = pf_results.Sf
        has_nonzero_flows = bool(np.any(np.real(sf) != 0.0))
        results["details"]["has_nonzero_flows"] = has_nonzero_flows
        results["details"]["max_flow_mw"] = float(np.max(np.abs(np.real(sf))))
        results["details"]["mean_flow_mw"] = float(np.mean(np.abs(np.real(sf))))

        # Voltage magnitude stats (should be 1.0 for DC)
        results["details"]["vm_min"] = float(np.min(magnitudes))
        results["details"]["vm_max"] = float(np.max(magnitudes))

        # Losses
        losses = pf_results.losses
        total_losses_mw = float(np.sum(np.real(losses)))
        results["details"]["total_losses_mw"] = total_losses_mw

        # 5. Check pass condition
        pass_checks = {
            "dcpf_converged": converged,
            "has_nonzero_angles": results["details"]["has_nonzero_angles"],
            "has_nonzero_flows": has_nonzero_flows,
        }
        results["details"]["pass_checks"] = pass_checks

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
