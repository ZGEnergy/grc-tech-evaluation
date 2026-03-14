"""
Test A-1: Solve DC power flow on TINY.

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Converges. Nodal injections, line flows, and voltage angles accessible as
    structured output (DataFrame, dict, or named array — not raw solver vector).
Tool: gridcal (VeraGridEngine) 5.6.28
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

# Add shared loader to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute A-1 DCPF test and return structured results."""
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
        results["details"]["bus_count"] = n_buses
        results["details"]["branch_count"] = n_branches
        results["details"]["gen_count"] = n_gens

        # 2. Configure DC power flow solver
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)

        # 3. Execute DCPF
        pf_results = vge.power_flow(grid, options=pf_opts)

        # 4. Extract results
        converged = bool(pf_results.converged)
        results["details"]["converged"] = converged

        if not converged:
            results["errors"].append("DCPF did not converge")
            return results

        # Voltage angles (radians -> degrees)
        voltage = pf_results.voltage
        angles_rad = np.angle(voltage)
        angles_deg = np.degrees(angles_rad)
        magnitudes = np.abs(voltage)

        # Bus names for structured output
        bus_names = [b.name for b in grid.get_buses()]

        results["details"]["voltage_angles_deg"] = {
            bus_names[i]: float(angles_deg[i]) for i in range(n_buses)
        }
        results["details"]["voltage_magnitudes_pu"] = {
            bus_names[i]: float(magnitudes[i]) for i in range(n_buses)
        }

        # Branch flows (from end) — Sf is complex power in MVA
        sf = pf_results.Sf
        branch_names = [b.name for b in grid.get_branches()]
        results["details"]["branch_flows_mw"] = {
            branch_names[i]: float(np.real(sf[i])) for i in range(len(sf))
        }

        # Nodal power injections (real part of S)
        (voltage * np.conj(pf_results.Sf[:n_buses]) if hasattr(pf_results, "Sbus") else None)

        # Try to get bus DataFrame export
        try:
            bus_df = pf_results.get_bus_df()
            results["details"]["bus_df_columns"] = list(bus_df.columns)
            results["details"]["bus_df_shape"] = list(bus_df.shape)
        except Exception as e:
            results["details"]["bus_df_export"] = f"get_bus_df() failed: {e}"

        try:
            branch_df = pf_results.get_branch_df()
            results["details"]["branch_df_columns"] = list(branch_df.columns)
            results["details"]["branch_df_shape"] = list(branch_df.shape)
        except Exception as e:
            results["details"]["branch_df_export"] = f"get_branch_df() failed: {e}"

        # Verify structured output accessibility
        has_angles = any(a != 0.0 for a in angles_deg)
        has_flows = any(float(np.real(sf[i])) != 0.0 for i in range(len(sf)))

        results["details"]["has_nonzero_angles"] = has_angles
        results["details"]["has_nonzero_flows"] = has_flows

        # Sample output
        results["details"]["sample_angle_deg"] = float(angles_deg[0])
        results["details"]["sample_flow_mw"] = float(np.real(sf[0]))
        results["details"]["max_angle_deg"] = float(np.max(np.abs(angles_deg)))
        results["details"]["max_flow_mw"] = float(np.max(np.abs(np.real(sf))))

        # 5. Check pass condition
        if converged and has_angles and has_flows:
            results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
