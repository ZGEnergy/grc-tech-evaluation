"""C-7: Solver Swap on ACTIVSg10k (MEDIUM, 10000 buses).

Dimension: scalability
Network: MEDIUM
Pass condition: DC OPF solves with both HiGHS and SCIP on 10k-bus network.
Only 2 solvers available (CBC and GLPK not available).
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute C-7 solver swap scalability test on MEDIUM network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "case_ACTIVSg10k (MEDIUM, 10000 buses)"

        # Load network
        t_load_0 = time.perf_counter()
        grid = vge.open_file(NETWORK_FILE)
        t_load = time.perf_counter() - t_load_0
        details["load_time_seconds"] = round(t_load, 6)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)

        solver_results = {}
        overall_peak_mem = 0.0

        for solver_name, solver_enum in [("HiGHS", MIPSolvers.HIGHS), ("SCIP", MIPSolvers.SCIP)]:
            opts = vge.OptimalPowerFlowOptions()
            opts.mip_solver = solver_enum

            tracemalloc.start()
            t0 = time.perf_counter()
            results = vge.linear_opf(grid, options=opts)
            wc = time.perf_counter() - t0
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            peak_mb = round(peak_mem / (1024 * 1024), 2)
            overall_peak_mem = max(overall_peak_mem, peak_mb)

            entry = {
                "wall_clock_seconds": round(wc, 6),
                "peak_memory_mb": peak_mb,
                "converged": bool(results.converged),
            }

            if results.converged:
                entry["total_generation_mw"] = round(float(results.generator_power.sum()), 4)
                entry["active_generators"] = int(np.sum(results.generator_power > 0.01))
                entry["shadow_price_range"] = [
                    round(float(results.bus_shadow_prices.min()), 6),
                    round(float(results.bus_shadow_prices.max()), 6),
                ]
                entry["lmp_mean"] = round(float(results.bus_shadow_prices.mean()), 6)

                loading = results.loading
                entry["max_loading_pct"] = round(float(np.max(np.abs(loading))) * 100, 2)
                binding = np.where(np.abs(loading) > 0.99)[0]
                entry["binding_branch_count"] = int(len(binding))
            else:
                errors.append(f"DC OPF did not converge with {solver_name}")

            solver_results[solver_name] = entry

        details["solver_results"] = solver_results
        details["solvers_available"] = ["HiGHS", "SCIP"]
        details["solvers_not_available"] = ["CBC", "GLPK"]

        # Compare results if both converged
        if solver_results["HiGHS"]["converged"] and solver_results["SCIP"]["converged"]:
            gen_diff = abs(
                solver_results["HiGHS"]["total_generation_mw"]
                - solver_results["SCIP"]["total_generation_mw"]
            )
            details["generation_diff_mw"] = round(gen_diff, 4)
            details["speedup_highs_vs_scip"] = (
                round(
                    solver_results["SCIP"]["wall_clock_seconds"]
                    / solver_results["HiGHS"]["wall_clock_seconds"],
                    2,
                )
                if solver_results["HiGHS"]["wall_clock_seconds"] > 0
                else None
            )

        # Use HiGHS timing as primary
        wall_clock = solver_results["HiGHS"]["wall_clock_seconds"]
        details["wall_clock_seconds"] = wall_clock
        details["peak_memory_mb"] = overall_peak_mem

        all_converged = all(r["converged"] for r in solver_results.values())
        status = (
            "pass"
            if all_converged
            else "qualified_pass"
            if any(r["converged"] for r in solver_results.values())
            else "fail"
        )

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "peak_memory_mb": details.get("peak_memory_mb"),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
