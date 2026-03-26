"""
Test C-3: DC OPF on MEDIUM (ACTIVSg 10k)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses, 12,706 branches, 2,485 generators)
Pass condition: Completes. Objectives consistent. Max branch loading reported;
    if >1.0+1e-4, record soft-constraint finding.
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
    """Return (threads_used, threads_available). pandapower DCOPF is single-threaded."""
    available = os.cpu_count() or 1
    return 1, available


def run(
    network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute DC OPF on MEDIUM network with PYPOWER PIPS solver."""
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
        base_mva = float(net.sn_mva)
        results["details"]["base_mva"] = base_mva
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["ext_grid_count"] = len(net.ext_grid)

        # Start memory tracking
        tracemalloc.start()

        # =========================================================
        # Run DC OPF with default PYPOWER PIPS solver
        # =========================================================
        solve_start = time.perf_counter()
        pp.rundcopp(net)
        solve_time = time.perf_counter() - solve_start

        # Peak memory
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)

        results["details"]["solve_wall_clock_seconds"] = solve_time

        # pandapower sets net.converged for power flow, net.OPF_converged for OPF
        opf_converged = getattr(net, "OPF_converged", False)
        pf_converged = getattr(net, "converged", False)
        results["details"]["opf_converged"] = opf_converged
        results["details"]["pf_converged"] = pf_converged

        if not opf_converged:
            results["errors"].append("DC OPF did not converge on MEDIUM network")
            return results

        results["details"]["converged"] = True

        # Objective value (total generation cost)
        results["details"]["objective_value"] = float(net.res_cost)

        # Generator dispatch
        total_gen_mw = float(net.res_gen["p_mw"].sum())
        total_ext_grid_mw = float(net.res_ext_grid["p_mw"].sum())
        total_load_mw = float(net.res_load["p_mw"].sum())

        results["details"]["total_gen_mw"] = total_gen_mw
        results["details"]["total_ext_grid_mw"] = total_ext_grid_mw
        results["details"]["total_load_mw"] = total_load_mw
        results["details"]["total_dispatch_mw"] = total_gen_mw + total_ext_grid_mw

        # =========================================================
        # Max branch loading — soft constraint check
        # =========================================================
        line_loading = net.res_line["loading_percent"]
        max_line_loading_pct = float(line_loading.max())
        mean_line_loading_pct = float(line_loading.mean())

        results["details"]["max_line_loading_pct"] = max_line_loading_pct
        results["details"]["mean_line_loading_pct"] = mean_line_loading_pct

        # Transformer loading
        max_trafo_loading_pct = 0.0
        if len(net.res_trafo) > 0:
            trafo_loading = net.res_trafo["loading_percent"]
            max_trafo_loading_pct = float(trafo_loading.max())
            results["details"]["max_trafo_loading_pct"] = max_trafo_loading_pct

        # Overall max branch loading (line or trafo)
        max_branch_loading = max(max_line_loading_pct, max_trafo_loading_pct)
        results["details"]["max_branch_loading_pct"] = max_branch_loading

        # Soft constraint check: loading > 100% + tolerance (1e-4 p.u. = 0.01%)
        soft_constraint_threshold = 100.0 + 0.01  # 100% + 0.01%
        if max_branch_loading > soft_constraint_threshold:
            results["details"]["soft_constraint_detected"] = True
            # Count violations
            n_line_violations = int((line_loading > soft_constraint_threshold).sum())
            results["details"]["line_violations_count"] = n_line_violations
            if len(net.res_trafo) > 0:
                n_trafo_violations = int(
                    (net.res_trafo["loading_percent"] > soft_constraint_threshold).sum()
                )
                results["details"]["trafo_violations_count"] = n_trafo_violations
        else:
            results["details"]["soft_constraint_detected"] = False

        # Bus angle stats
        va = net.res_bus["va_degree"]
        results["details"]["va_min_deg"] = float(va.min())
        results["details"]["va_max_deg"] = float(va.max())

        # Number of generators at limits
        gen_at_pmax = 0
        gen_at_pmin = 0
        for idx in net.gen.index:
            p = net.res_gen.at[idx, "p_mw"]
            pmax = net.gen.at[idx, "max_p_mw"]
            pmin = net.gen.at[idx, "min_p_mw"]
            if abs(p - pmax) < 1e-3:
                gen_at_pmax += 1
            if abs(p - pmin) < 1e-3:
                gen_at_pmin += 1

        results["details"]["gen_at_pmax"] = gen_at_pmax
        results["details"]["gen_at_pmin"] = gen_at_pmin
        results["details"]["gen_active_count"] = len(net.gen)

        results["details"]["solver"] = "PYPOWER PIPS (internal)"
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
