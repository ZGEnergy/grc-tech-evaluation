"""
Test A-1: Solve DC power flow

Dimension: expressiveness
Network: TINY (case39)
Pass condition: Converges. Nodal injections, line flows, and voltage angles accessible
    as structured output (DataFrame, dict, or named array -- not raw solver vector).
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")


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
    try:
        ppc["gencost"] = cf.gencost.values
    except Exception:
        pass

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute DC power flow and return structured results.

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

        # 2. Solve DCPF (timed)
        start = time.perf_counter()
        info = n.lpf()
        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed

        # 3. Check convergence
        # n.lpf() returns a dict or DataFrame with convergence info
        # For PyPSA, lpf is a direct linear solve -- always converges if the system is valid
        converged = True
        if hasattr(info, "converged"):
            converged = bool(info.converged.all())
        elif isinstance(info, dict) and "converged" in info:
            converged = bool(info["converged"])

        # 4. Extract and validate structured outputs
        # Voltage angles
        v_ang = n.buses_t.v_ang
        has_angles = v_ang is not None and len(v_ang) > 0
        angle_stats = {}
        if has_angles:
            angles_rad = v_ang.iloc[0]
            angle_stats = {
                "min_rad": float(angles_rad.min()),
                "max_rad": float(angles_rad.max()),
                "mean_rad": float(angles_rad.mean()),
                "num_buses": int(len(angles_rad)),
            }

        # Line flows (p0 = sending end active power)
        line_flows = n.lines_t.p0
        has_flows = line_flows is not None and len(line_flows) > 0
        flow_stats = {}
        if has_flows:
            flows = line_flows.iloc[0]
            flow_stats = {
                "min_MW": float(flows.min()),
                "max_MW": float(flows.max()),
                "mean_MW": float(flows.mean()),
                "num_lines": int(len(flows)),
            }

        # Nodal power injections (p = active power at each bus)
        bus_p = n.buses_t.p
        has_injections = bus_p is not None and len(bus_p) > 0
        injection_stats = {}
        if has_injections:
            injections = bus_p.iloc[0]
            injection_stats = {
                "min_MW": float(injections.min()),
                "max_MW": float(injections.max()),
                "sum_MW": float(injections.sum()),
                "num_buses": int(len(injections)),
            }

        # 5. Determine output format
        output_format = "pandas DataFrame"

        # 6. Check pass condition
        pass_condition_met = (
            converged
            and has_angles
            and has_flows
            and has_injections
            and angle_stats["num_buses"] > 0
            and flow_stats["num_lines"] > 0
        )

        if pass_condition_met:
            results["status"] = "pass"

        results["details"] = {
            "converged": converged,
            "output_format": output_format,
            "voltage_angles": angle_stats,
            "line_flows": flow_stats,
            "nodal_injections": injection_stats,
            "v_ang_type": str(type(v_ang)),
            "p0_type": str(type(line_flows)),
            "bus_p_type": str(type(bus_p)),
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
