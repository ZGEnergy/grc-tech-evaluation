"""A-3: DC OPF with gen costs and line flow limits on IEEE 39-bus (TINY)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def _run_dcopf(grid, solver_enum, solver_name: str) -> dict:
    """Run DC OPF with given solver and return results dict."""
    import VeraGridEngine as vge

    opts = vge.OptimalPowerFlowOptions()
    opts.mip_solver = solver_enum

    t0 = time.perf_counter()
    results = vge.linear_opf(grid, options=opts)
    wall_clock = time.perf_counter() - t0

    converged = bool(results.converged)
    result = {
        "solver": solver_name,
        "converged": converged,
        "wall_clock_seconds": round(wall_clock, 6),
    }

    if converged:
        result["generator_dispatch_mw"] = [round(float(x), 4) for x in results.generator_power]
        result["total_generation_mw"] = round(float(results.generator_power.sum()), 4)
        result["shadow_prices"] = [round(float(x), 6) for x in results.bus_shadow_prices]
        result["shadow_price_range"] = [
            round(float(results.bus_shadow_prices.min()), 6),
            round(float(results.bus_shadow_prices.max()), 6),
        ]
        result["lmp_uniform"] = bool(
            np.allclose(results.bus_shadow_prices, results.bus_shadow_prices[0], atol=1e-6)
        )

        # Branch flows
        sf = results.Sf
        result["branch_flow_range_mw"] = [round(float(sf.min()), 2), round(float(sf.max()), 2)]

        # Check for binding line limits
        loading = results.loading
        result["max_loading_pct"] = round(float(np.max(np.abs(loading))) * 100, 2)
        binding = np.where(np.abs(loading) > 0.99)[0]
        result["binding_branch_count"] = int(len(binding))

        # Generation shedding and load shedding
        if hasattr(results, "generator_shedding"):
            result["gen_shedding_total_mw"] = round(
                float(np.sum(np.abs(results.generator_shedding))), 4
            )
        if hasattr(results, "load_shedding"):
            result["load_shedding_total_mw"] = round(
                float(np.sum(np.abs(results.load_shedding))), 4
            )

    return result


def run() -> dict:
    """Execute A-3 DC OPF test and return structured results."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # Load network
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)

        # Document generator cost curves
        gen_costs = []
        for i, g in enumerate(grid.generators):
            gen_costs.append(
                {
                    "index": i,
                    "name": g.name,
                    "Cost": g.Cost,
                    "Cost2": g.Cost2,
                    "Cost0": g.Cost0,
                    "Pmin": g.Pmin,
                    "Pmax": g.Pmax,
                }
            )
        details["generator_costs"] = gen_costs

        # Check branch flow limits
        branches = list(grid.lines) + list(grid.transformers2w)
        rates = [b.rate for b in branches]
        details["branches_with_rate"] = sum(1 for r in rates if r > 0)
        details["branches_total"] = len(branches)

        # ── Run with HiGHS ──
        highs_result = _run_dcopf(grid, MIPSolvers.HIGHS, "HiGHS")
        details["highs"] = highs_result

        # ── Run with GLPK ──
        # GridCal uses CBC enum value — check if GLPK is available
        glpk_result = None
        try:
            glpk_result = _run_dcopf(grid, MIPSolvers.CBC, "CBC (GLPK substitute)")
            details["cbc"] = glpk_result
        except Exception as e:
            details["cbc_error"] = str(e)
            # Try SCIP as another alternative
            try:
                scip_result = _run_dcopf(grid, MIPSolvers.SCIP, "SCIP")
                details["scip"] = scip_result
            except Exception as e2:
                details["scip_error"] = str(e2)

        # Overall timing from primary solver
        wall_clock = highs_result["wall_clock_seconds"]
        details["wall_clock_seconds"] = wall_clock
        details["primary_solver"] = "HiGHS"

        # Output format documentation
        details["output_format"] = (
            "OptimalPowerFlowResults: generator_power (Vec), bus_shadow_prices (Vec), "
            "Sf/St (Vec), loading (Vec), generator_shedding (Vec), load_shedding (Vec). "
            "All numpy arrays. No built-in DataFrame accessor on OPF results."
        )

        # Note about cost curves
        details["cost_curve_note"] = (
            "All 10 generators have identical linear cost (0.3 $/MWh) in case39.m, "
            "so LMPs are uniform at 0.3 when no lines are binding. "
            "GridCal supports linear (Cost), quadratic (Cost2), and constant (Cost0) cost terms."
        )

        # Check for pass
        if highs_result["converged"]:
            status = "pass"
        else:
            status = "fail"
            errors.append("DC OPF did not converge with HiGHS")

    except Exception as e:
        errors.append(f"Exception: {type(e).__name__}: {e}")
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
