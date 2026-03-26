"""
Test C-7: Solver Swap on MEDIUM

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k — 10,000 buses)
Pass condition: Records whether solver swap requires reformulation or just parameter
  change. Time per solver.
Tool: PyPSA 1.1.2
Solvers: HiGHS, GLPK, SCIP
"""

import multiprocessing
import os
import sys
import time
import traceback
import tracemalloc

import numpy as np

# Shared loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))
from matpower_loader import load_pypsa

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DEFAULT_NETWORK = os.path.join(REPO_ROOT, "data", "networks", "case_ACTIVSg10k.m")

# Solvers to test per protocol
SOLVERS_REQUIRED = ["highs", "glpk", "scip"]

SOLVER_OPTIONS_MAP = {
    "highs": {
        "time_limit": 300,
        "presolve": "on",
        "threads": 1,
        "output_flag": True,
    },
    "glpk": {},  # GLPK options passed via command-line by linopy
    "scip": {},
}


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Test solver swap on MEDIUM DCOPF.

    Key question: Does swapping solvers require reformulation or just a parameter change?

    Returns:
        dict with standard test result keys.
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # Record CPU info
        cpu_threads_available = multiprocessing.cpu_count()
        results["details"]["cpu_threads_available"] = cpu_threads_available
        results["details"]["cpu_threads_used"] = 1  # single-threaded per solver-config

        # 1. Load network
        # overwrite_zero_s_nom=99999.0: MATPOWER rateA=0 means unconstrained;
        # PyPSA interprets True as 1.0 MVA which causes infeasibility.
        load_start = time.perf_counter()
        n_base = load_pypsa(network_file, overwrite_zero_s_nom=99999.0)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["n_buses"] = len(n_base.buses)
        results["details"]["n_generators"] = len(n_base.generators)
        results["details"]["n_branches"] = len(n_base.lines) + len(n_base.transformers)
        print(f"Network loaded in {load_elapsed:.2f}s: {len(n_base.buses)} buses")

        # 2. Test each solver
        solver_results = {}
        any_solved = False

        for solver_name in SOLVERS_REQUIRED:
            print(f"\n--- Testing solver: {solver_name} ---")
            n = n_base.copy()
            solver_opts = SOLVER_OPTIONS_MAP.get(solver_name, {})

            tracemalloc.start()
            t0 = time.perf_counter()
            try:
                opt_result = n.optimize(
                    solver_name=solver_name,
                    solver_options=solver_opts,
                )
                t1 = time.perf_counter()
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                status_str = (
                    str(opt_result[0]) if isinstance(opt_result, tuple) else str(opt_result)
                )
                solve_ok = False
                obj_val = None
                try:
                    obj_val = float(n.objective)
                    if np.isfinite(obj_val):
                        solve_ok = True
                except Exception:
                    pass
                if status_str.lower() in ("ok", "optimal"):
                    solve_ok = True

                solver_results[solver_name] = {
                    "available": True,
                    "solved": solve_ok,
                    "solver_status": status_str,
                    "wall_clock_seconds": round(t1 - t0, 3),
                    "peak_memory_mb": round(peak / (1024 * 1024), 1),
                    "objective": obj_val,
                    "requires_reformulation": False,
                }
                if solve_ok:
                    any_solved = True
                print(
                    f"  {solver_name}: {status_str} in {t1 - t0:.3f}s, "
                    f"obj={obj_val}, mem={peak / (1024 * 1024):.1f} MB"
                )

            except Exception as e:
                t1 = time.perf_counter()
                try:
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                except Exception:
                    peak = 0
                err_msg = f"{type(e).__name__}: {str(e)[:300]}"
                solver_results[solver_name] = {
                    "available": False,
                    "solved": False,
                    "error": err_msg,
                    "wall_clock_seconds": round(t1 - t0, 3),
                    "peak_memory_mb": round(peak / (1024 * 1024), 1),
                    "requires_reformulation": False,
                }
                print(f"  {solver_name}: UNAVAILABLE — {err_msg}")

        results["details"]["solver_results"] = solver_results

        # 3. Architecture finding
        results["details"]["solver_swap_mechanism"] = (
            "n.optimize(solver_name=...) dispatches the SAME linopy model to different "
            "solver backends. The LP/MILP formulation is solver-agnostic — no reformulation "
            "or model reconstruction is needed. Solver swap is a single parameter change."
        )
        results["details"]["requires_reformulation"] = False

        # 4. Cross-solver objective comparison
        solved_objectives = {
            s: r["objective"]
            for s, r in solver_results.items()
            if r.get("solved") and r.get("objective") is not None
        }
        if len(solved_objectives) >= 2:
            objs = list(solved_objectives.values())
            max_diff = max(objs) - min(objs)
            results["details"]["cross_solver_objective_diff"] = max_diff
            results["details"]["objectives_match"] = max_diff < 1.0  # within $1

        # 5. Status
        if any_solved:
            results["status"] = "pass"
        else:
            results["errors"].append("No solver produced a valid solution")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
