"""C-3: DC OPF Scale on ACTIVSg10k (MEDIUM, 10000 buses).

Dimension: scalability
Network: MEDIUM
Pass condition: DC OPF solves with HiGHS on 10k-bus network within 600s.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute C-3 DC OPF scalability test on MEDIUM network."""
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

        # ── Run DC OPF with HiGHS ──
        opts = vge.OptimalPowerFlowOptions()
        opts.mip_solver = MIPSolvers.HIGHS

        tracemalloc.start()
        t0 = time.perf_counter()
        results = vge.linear_opf(grid, options=opts)
        wall_clock_highs = time.perf_counter() - t0
        _, peak_mem_highs = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        details["highs"] = {
            "wall_clock_seconds": round(wall_clock_highs, 6),
            "peak_memory_mb": round(peak_mem_highs / (1024 * 1024), 2),
            "converged": bool(results.converged),
        }

        if results.converged:
            details["highs"]["total_generation_mw"] = round(float(results.generator_power.sum()), 4)
            details["highs"]["active_generators"] = int(np.sum(results.generator_power > 0.01))
            details["highs"]["shadow_price_range"] = [
                round(float(results.bus_shadow_prices.min()), 6),
                round(float(results.bus_shadow_prices.max()), 6),
            ]
            details["highs"]["lmp_mean"] = round(float(results.bus_shadow_prices.mean()), 6)
            loading = results.loading
            details["highs"]["max_loading_pct"] = round(float(np.max(np.abs(loading))) * 100, 2)
            binding = np.where(np.abs(loading) > 0.99)[0]
            details["highs"]["binding_branch_count"] = int(len(binding))

            if hasattr(results, "load_shedding"):
                details["highs"]["load_shedding_total_mw"] = round(
                    float(np.sum(np.abs(results.load_shedding))), 4
                )
        else:
            errors.append("DC OPF did not converge on MEDIUM network with HiGHS")

        wall_clock = wall_clock_highs
        peak_memory_mb = details["highs"]["peak_memory_mb"]
        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["peak_memory_mb"] = peak_memory_mb
        details["solver"] = "HiGHS"

        status = "pass" if results.converged else "fail"

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
