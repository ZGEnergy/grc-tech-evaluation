"""A-3: DC OPF on ACTIVSg10k (MEDIUM, 10000 buses)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute A-3 DC OPF test on MEDIUM network."""
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

        branches = list(grid.lines) + list(grid.transformers2w)
        details["branches_total"] = len(branches)
        details["branches_with_rate"] = sum(1 for b in branches if b.rate > 0)

        # Run DC OPF with HiGHS
        opts = vge.OptimalPowerFlowOptions()
        opts.mip_solver = MIPSolvers.HIGHS

        t0 = time.perf_counter()
        results = vge.linear_opf(grid, options=opts)
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["converged"] = bool(results.converged)

        if not results.converged:
            errors.append("DC OPF did not converge on MEDIUM network with HiGHS")
            return {
                "status": "fail",
                "wall_clock_seconds": wall_clock,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        # Extract results
        details["total_generation_mw"] = round(float(results.generator_power.sum()), 4)
        details["gen_dispatch_range_mw"] = [
            round(float(results.generator_power.min()), 4),
            round(float(results.generator_power.max()), 4),
        ]
        details["active_generators"] = int(np.sum(results.generator_power > 0.01))

        # Shadow prices (LMPs)
        details["shadow_price_range"] = [
            round(float(results.bus_shadow_prices.min()), 6),
            round(float(results.bus_shadow_prices.max()), 6),
        ]
        details["lmp_uniform"] = bool(
            np.allclose(results.bus_shadow_prices, results.bus_shadow_prices[0], atol=1e-6)
        )
        details["lmp_mean"] = round(float(results.bus_shadow_prices.mean()), 6)

        # Branch flows
        sf = results.Sf
        details["branch_flow_range_mw"] = [round(float(sf.min()), 2), round(float(sf.max()), 2)]

        # Loading
        loading = results.loading
        details["max_loading_pct"] = round(float(np.max(np.abs(loading))) * 100, 2)
        binding = np.where(np.abs(loading) > 0.99)[0]
        details["binding_branch_count"] = int(len(binding))

        # Shedding
        if hasattr(results, "generator_shedding"):
            details["gen_shedding_total_mw"] = round(
                float(np.sum(np.abs(results.generator_shedding))), 4
            )
        if hasattr(results, "load_shedding"):
            details["load_shedding_total_mw"] = round(
                float(np.sum(np.abs(results.load_shedding))), 4
            )

        details["solver"] = "HiGHS"
        status = "pass"

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
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
