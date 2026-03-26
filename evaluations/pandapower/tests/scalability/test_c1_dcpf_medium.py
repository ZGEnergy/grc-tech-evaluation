"""
Test C-1: DCPF on MEDIUM (ACTIVSg 10k)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses, 12,706 branches, 2,485 generators)
Pass condition: Completes successfully
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower


def _get_cpu_info() -> tuple[int, int]:
    """Return (threads_used, threads_available). pandapower DCPF is single-threaded."""
    available = os.cpu_count() or 1
    return 1, available


def run(
    network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute DCPF on MEDIUM network and record scalability metrics."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandapower as pp

        # Load network
        net = load_pandapower(network_file)

        # Thread reporting
        threads_used, threads_available = _get_cpu_info()
        results["details"]["cpu_threads_used"] = threads_used
        results["details"]["cpu_threads_available"] = threads_available

        # Network stats
        results["details"]["base_mva"] = float(net.sn_mva)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["ext_grid_count"] = len(net.ext_grid)

        # Start memory tracking
        tracemalloc.start()

        # Run DCPF — timed solve only (network loading excluded)
        solve_start = time.perf_counter()
        pp.rundcpp(net)
        solve_time = time.perf_counter() - solve_start

        # Peak memory
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)

        results["details"]["solve_wall_clock_seconds"] = solve_time

        if not net.converged:
            results["errors"].append("DCPF did not converge on MEDIUM network")
            return results

        # Extract key results
        results["details"]["converged"] = True

        # Bus voltage angles
        va = net.res_bus["va_degree"]
        results["details"]["va_min_deg"] = float(va.min())
        results["details"]["va_max_deg"] = float(va.max())
        results["details"]["va_mean_deg"] = float(va.mean())

        # Branch flows
        line_loading = net.res_line["loading_percent"]
        results["details"]["max_line_loading_pct"] = float(line_loading.max())
        results["details"]["mean_line_loading_pct"] = float(line_loading.mean())

        # Power balance
        total_gen_mw = float(net.res_gen["p_mw"].sum())
        total_ext_grid_mw = float(net.res_ext_grid["p_mw"].sum())
        total_load_mw = float(net.res_load["p_mw"].sum())
        total_loss_mw = float(net.res_line["pl_mw"].sum())
        if len(net.res_trafo) > 0:
            total_loss_mw += float(net.res_trafo["pl_mw"].sum())

        results["details"]["total_gen_mw"] = total_gen_mw
        results["details"]["total_ext_grid_mw"] = total_ext_grid_mw
        results["details"]["total_load_mw"] = total_load_mw
        results["details"]["total_loss_mw"] = total_loss_mw

        # Transformer loading
        if len(net.res_trafo) > 0:
            trafo_loading = net.res_trafo["loading_percent"]
            results["details"]["max_trafo_loading_pct"] = float(trafo_loading.max())

        results["details"]["pandapower_version"] = pp.__version__

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        try:
            tracemalloc.stop()
        except RuntimeError:
            pass
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
