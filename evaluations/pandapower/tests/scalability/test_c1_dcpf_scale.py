"""
Test C-1: DCPF at scale

Dimension: scalability
Network: MEDIUM (ACTIVSg10k, ~10000 buses)
Pass condition: Converges on MEDIUM network.
Tool: pandapower v3.4.0
"""

import json
import os
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute DCPF at scale and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        load_start = time.perf_counter()
        net = from_mpc(network_file, f_hz=60)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["ext_grid_count"] = len(net.ext_grid)
        results["details"]["load_count"] = len(net.load)

        # 2. Memory before solve
        try:
            import resource

            mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB on Linux
        except Exception:
            mem_before = None

        # 3. Solve DCPF (timed)
        solve_start = time.perf_counter()
        pp.rundcpp(net)
        solve_elapsed = time.perf_counter() - solve_start
        results["details"]["solve_seconds"] = solve_elapsed

        # Memory after solve
        try:
            mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            results["details"]["peak_memory_mb"] = mem_after
            if mem_before is not None:
                results["details"]["memory_delta_mb"] = mem_after - mem_before
        except Exception:
            pass

        # CPU utilization estimate
        try:
            cpu_times = os.times()
            results["details"]["cpu_user_seconds"] = cpu_times.user
            results["details"]["cpu_system_seconds"] = cpu_times.system
        except Exception:
            pass

        # 4. Verify convergence
        if not net["converged"]:
            results["errors"].append("DCPF did not converge on MEDIUM network")
            return results

        # 5. Extract summary results
        va = net.res_bus["va_degree"]
        results["details"]["total_buses_with_results"] = len(net.res_bus)
        results["details"]["total_lines_with_results"] = len(net.res_line)
        results["details"]["va_max_deg"] = float(va.max())
        results["details"]["va_min_deg"] = float(va.min())
        results["details"]["max_line_flow_mw"] = float(net.res_line["p_from_mw"].abs().max())

        # 6. Check pass condition
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
