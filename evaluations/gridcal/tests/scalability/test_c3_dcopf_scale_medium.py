"""
Test C-3: DC OPF on MEDIUM with HiGHS and GLPK.

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: Solves with both solvers.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS, GLPK (GLPK not available in GridCal — using SCIP as alternative)

Note: GridCal's MIPSolvers enum does not include GLPK. The enum lists
HIGHS, SCIP, CPLEX, GUROBI, XPRESS, CBC, PDLP — but the PuLP interface
only maps HIGHS, SCIP, CPLEX, GUROBI, XPRESS. CBC/PDLP raise runtime errors.
SCIP is used as the GLPK substitute (open-source LP/MILP solver).
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


def solve_dcopf(network_file: str, solver_enum, solver_name: str) -> dict:
    """Solve DC OPF with a specific solver and return results dict."""
    import VeraGridEngine as vge
    from VeraGridEngine.enumerations import SolverType

    grid = load_gridcal(network_file)
    generators = grid.get_generators()
    branches = grid.get_branches()
    n_buses = grid.get_bus_number()
    n_gens = len(generators)
    n_branches = len(branches)

    opf_opts = vge.OptimalPowerFlowOptions(
        solver=SolverType.LINEAR_OPF,
        mip_solver=solver_enum,
    )

    tracemalloc.start()
    solve_start = time.perf_counter()
    opf_results = vge.linear_opf(grid, opf_opts)
    solve_elapsed = time.perf_counter() - solve_start
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    converged = bool(opf_results.converged)

    result = {
        "solver": solver_name,
        "converged": converged,
        "wall_clock_seconds": solve_elapsed,
        "peak_memory_mb": peak_mem / (1024 * 1024),
        "bus_count": n_buses,
        "gen_count": n_gens,
        "branch_count": n_branches,
    }

    if converged:
        gen_power = opf_results.generator_power
        lmps = opf_results.bus_shadow_prices
        loading = np.abs(opf_results.loading)

        result["total_gen_mw"] = float(np.sum(gen_power))
        result["gen_dispatch_range"] = {
            "min": float(np.min(gen_power)),
            "max": float(np.max(gen_power)),
        }

        if lmps is not None and len(lmps) > 0:
            result["lmp_range"] = {
                "min": float(np.min(lmps)),
                "max": float(np.max(lmps)),
                "mean": float(np.mean(lmps)),
                "spread": float(np.max(lmps) - np.min(lmps)),
            }

        result["max_loading_pct"] = float(np.max(loading) * 100)
        binding = int(np.sum(loading >= 0.99))
        result["binding_branch_count"] = binding

    return result


def run(
    network_file: str = "data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute C-3 DCOPF scale test on MEDIUM with HiGHS and SCIP."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        from VeraGridEngine.enumerations import MIPSolvers

        results["details"]["glpk_note"] = (
            "GLPK is not available in GridCal's MIPSolvers enum. "
            "The enum lists HIGHS, SCIP, CPLEX, GUROBI, XPRESS, CBC, PDLP — "
            "but the PuLP interface only maps HIGHS, SCIP, CPLEX, GUROBI, XPRESS. "
            "CBC/PDLP raise runtime errors despite being in the enum. "
            "Using SCIP as the GLPK substitute (open-source LP/MILP solver)."
        )

        # Solve with HiGHS
        highs_result = solve_dcopf(network_file, MIPSolvers.HIGHS, "HiGHS")
        results["details"]["highs"] = highs_result

        # Solve with SCIP (GLPK substitute — both are open-source LP/MILP solvers)
        scip_result = solve_dcopf(network_file, MIPSolvers.SCIP, "SCIP")
        results["details"]["scip"] = scip_result

        # Cross-solver comparison
        if highs_result["converged"] and scip_result["converged"]:
            gen_diff = abs(highs_result["total_gen_mw"] - scip_result["total_gen_mw"])
            results["details"]["cross_solver_comparison"] = {
                "total_gen_diff_mw": gen_diff,
                "highs_time_s": highs_result["wall_clock_seconds"],
                "scip_time_s": scip_result["wall_clock_seconds"],
                "speedup_ratio": (
                    scip_result["wall_clock_seconds"] / highs_result["wall_clock_seconds"]
                    if highs_result["wall_clock_seconds"] > 0
                    else None
                ),
            }

        # Pass condition: both solvers converge
        pass_checks = {
            "highs_converged": highs_result["converged"],
            "scip_converged": scip_result["converged"],
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

        results["workarounds"].append(
            "GLPK is not in GridCal's MIPSolvers enum. SCIP used as substitute. "
            "This is a stable workaround — SCIP is a documented solver option in GridCal. "
            "Note: CBC is in the enum but raises 'PuLP Unsupported MIP solver' at runtime."
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
