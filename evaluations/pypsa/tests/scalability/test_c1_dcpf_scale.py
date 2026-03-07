"""
Test C-1: DC Power Flow Scale Test

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k)
Pass condition: Converges. Wall-clock and peak memory recorded.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import json
import math
import time
import traceback
from pathlib import Path

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

    # Fix zero impedance branches (causes singular matrix in LPF)
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
        return usage.ru_maxrss / 1024.0  # Linux returns KB
    except Exception:
        return None


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute DCPF on 10k-bus network and return structured results."""
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

        # Note workarounds applied during load
        zero_x_lines = (n.lines["x"] == 0.0001).sum()
        zero_x_xfmr = (n.transformers["x"] == 0.0001).sum()
        if zero_x_lines > 0 or zero_x_xfmr > 0:
            results["workarounds"].append(
                f"Set x=0.0001 on {zero_x_lines} lines and {zero_x_xfmr} transformers "
                "with zero reactance to avoid singular matrix"
            )

        network_stats = {
            "n_buses": len(n.buses),
            "n_generators": len(n.generators),
            "n_lines": len(n.lines),
            "n_transformers": len(n.transformers),
            "n_loads": len(n.loads),
        }

        load_elapsed = time.perf_counter() - start

        # 2. Solve DCPF (timed separately)
        solve_start = time.perf_counter()
        info = n.lpf()
        solve_elapsed = time.perf_counter() - solve_start

        mem_after = _get_peak_memory_mb()

        # 3. Check convergence
        converged = True
        if hasattr(info, "converged"):
            converged = bool(info.converged.all())

        # 4. Extract structured outputs
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

        total_elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = total_elapsed

        results["details"] = {
            "converged": converged,
            "load_time_seconds": load_elapsed,
            "solve_time_seconds": solve_elapsed,
            "network": network_stats,
            "voltage_angles": angle_stats,
            "line_flows": flow_stats,
            "nodal_injections": injection_stats,
            "peak_memory_mb": mem_after,
            "mem_before_mb": mem_before,
            "pypsa_version": pypsa.__version__,
        }

        if converged and has_angles and has_flows:
            results["status"] = "pass"

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
