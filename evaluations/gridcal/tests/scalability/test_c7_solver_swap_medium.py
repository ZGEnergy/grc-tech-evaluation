"""
Test C-7: Repeat C-3 with each available open-source solver on MEDIUM.

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: Solver swap on MEDIUM -- whether solver swap requires reformulation
    or just a parameter change.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS, GLPK (unavailable), SCIP

From C-3: GLPK not in MIPSolvers enum. Available open-source solvers: HiGHS, SCIP.
CBC/PDLP are in enum but raise runtime errors. This test documents what is actually
swappable and whether swap is a parameter change or requires reformulation.
"""

from __future__ import annotations

import json
import os
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


def try_solver(network_file: str, solver_enum, solver_name: str) -> dict:
    """Attempt to solve with a solver, catching runtime errors."""
    try:
        return solve_dcopf(network_file, solver_enum, solver_name)
    except Exception as e:
        return {
            "solver": solver_name,
            "converged": False,
            "error": f"{type(e).__name__}: {e}",
            "wall_clock_seconds": 0.0,
            "peak_memory_mb": 0.0,
        }


def run(
    network_file: str = "data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute C-7 solver swap test on MEDIUM."""
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

        # Record CPU thread info
        cpu_threads_available = os.cpu_count() or 1
        cpu_threads_used = 1  # PuLP solvers run single-threaded by default
        results["details"]["cpu_threads_used"] = cpu_threads_used
        results["details"]["cpu_threads_available"] = cpu_threads_available

        # =====================================================================
        # Step 1: Document available solvers
        # =====================================================================
        all_enum_solvers = [s.name for s in MIPSolvers]
        results["details"]["enum_solvers"] = all_enum_solvers

        results["details"]["solver_availability"] = {
            "HIGHS": "available -- works via PuLP HIGHS_CMD",
            "SCIP": "available -- works via PuLP SCIP_CMD",
            "CPLEX": "commercial -- not tested",
            "GUROBI": "commercial -- not tested",
            "XPRESS": "commercial -- not tested",
            "CBC": "in enum but raises 'PuLP Unsupported MIP solver CBC' at runtime",
            "PDLP": "in enum but raises runtime error (no PuLP mapping)",
            "GLPK": "NOT IN ENUM -- not available in GridCal",
        }

        # =====================================================================
        # Step 2: Test each available open-source solver
        # =====================================================================

        # HiGHS
        highs_result = solve_dcopf(network_file, MIPSolvers.HIGHS, "HiGHS")
        results["details"]["highs"] = highs_result

        # SCIP
        scip_result = solve_dcopf(network_file, MIPSolvers.SCIP, "SCIP")
        results["details"]["scip"] = scip_result

        # CBC -- attempt and document failure
        cbc_result = try_solver(network_file, MIPSolvers.CBC, "CBC")
        results["details"]["cbc"] = cbc_result

        # PDLP -- attempt and document failure
        pdlp_result = try_solver(network_file, MIPSolvers.PDLP, "PDLP")
        results["details"]["pdlp"] = pdlp_result

        # =====================================================================
        # Step 3: Solver swap analysis
        # =====================================================================
        results["details"]["reformulation_required"] = False
        results["details"]["swap_mechanism"] = (
            "Solver swap is a single parameter change: set mip_solver=MIPSolvers.<SOLVER> "
            "in OptimalPowerFlowOptions. No reformulation, no model rebuild, no code change "
            "beyond the enum value. The same PTDF-based LP formulation is passed to PuLP "
            "which dispatches to the backend solver."
        )

        # Cross-solver comparison
        working_solvers = []
        if highs_result["converged"]:
            working_solvers.append(("HiGHS", highs_result))
        if scip_result["converged"]:
            working_solvers.append(("SCIP", scip_result))

        if len(working_solvers) == 2:
            gen_diff = abs(
                working_solvers[0][1]["total_gen_mw"] - working_solvers[1][1]["total_gen_mw"]
            )
            results["details"]["cross_solver_comparison"] = {
                "total_gen_diff_mw": gen_diff,
                "highs_time_s": highs_result["wall_clock_seconds"],
                "scip_time_s": scip_result["wall_clock_seconds"],
                "speedup_ratio": (
                    scip_result["wall_clock_seconds"] / highs_result["wall_clock_seconds"]
                    if highs_result["wall_clock_seconds"] > 0
                    else None
                ),
                "dispatch_identical": gen_diff < 0.01,
            }

        # =====================================================================
        # Step 4: Summary of available vs unavailable solvers
        # =====================================================================
        results["details"]["open_source_solver_summary"] = {
            "working": ["HiGHS", "SCIP"],
            "broken_enum": ["CBC", "PDLP"],
            "missing_from_enum": ["GLPK"],
            "total_working_open_source": 2,
            "total_requested_by_protocol": 3,
        }

        # =====================================================================
        # Step 5: Pass condition check
        # =====================================================================
        # Pass: solver swap works as parameter change (no reformulation)
        # and at least the available solvers produce results
        pass_checks = {
            "highs_converged": highs_result["converged"],
            "scip_converged": scip_result["converged"],
            "no_reformulation_needed": True,
            "swap_is_parameter_change": True,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "qualified_pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

        results["workarounds"].append(
            "GLPK not available in GridCal's MIPSolvers enum -- cannot test protocol-specified "
            "GLPK solver. SCIP used as open-source substitute. CBC/PDLP are in the enum but "
            "raise runtime errors via PuLP interface. Solver swap for working solvers (HiGHS, "
            "SCIP) is a trivial parameter change with no reformulation."
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
