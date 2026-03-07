"""A-10: Lossy DC OPF on ACTIVSg2000 (SMALL, 2000 buses)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg2000.m")


def run() -> dict:
    """Lossy DC OPF on SMALL network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "case_ACTIVSg2000 (SMALL, 2000 buses)"

        # Load network
        t_load_0 = time.perf_counter()
        grid = vge.open_file(NETWORK_FILE)
        t_load = time.perf_counter() - t_load_0

        details["load_time_seconds"] = round(t_load, 6)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)
        branches = list(grid.lines) + list(grid.transformers2w)
        details["branches"] = len(branches)

        # ── Step 1: Lossless DC OPF ──
        opts_lossless = vge.OptimalPowerFlowOptions()
        opts_lossless.mip_solver = MIPSolvers.HIGHS

        t0 = time.perf_counter()
        res_lossless = vge.linear_opf(grid, options=opts_lossless)
        t_lossless = time.perf_counter() - t0

        details["lossless_dcopf"] = {
            "converged": bool(res_lossless.converged),
            "wall_clock_seconds": round(t_lossless, 6),
            "total_gen_mw": round(float(res_lossless.generator_power.sum()), 4),
            "shadow_price_range": [
                round(float(res_lossless.bus_shadow_prices.min()), 6),
                round(float(res_lossless.bus_shadow_prices.max()), 6),
            ],
            "lmp_uniform": bool(
                np.allclose(
                    res_lossless.bus_shadow_prices,
                    res_lossless.bus_shadow_prices[0],
                    atol=1e-6,
                )
            ),
        }

        # ── Step 2: Lossy DC OPF ──
        grid2 = vge.open_file(NETWORK_FILE)
        opts_lossy = vge.OptimalPowerFlowOptions()
        opts_lossy.mip_solver = MIPSolvers.HIGHS

        lossy_enabled = False
        if hasattr(opts_lossy, "add_losses_approximation"):
            opts_lossy.add_losses_approximation = True
            lossy_enabled = True
        elif hasattr(opts_lossy, "consider_losses"):
            opts_lossy.consider_losses = True
            lossy_enabled = True

        details["lossy_option_found"] = lossy_enabled

        if lossy_enabled:
            t0 = time.perf_counter()
            res_lossy = vge.linear_opf(grid2, options=opts_lossy)
            t_lossy = time.perf_counter() - t0

            details["lossy_dcopf"] = {
                "converged": bool(res_lossy.converged),
                "wall_clock_seconds": round(t_lossy, 6),
                "total_gen_mw": round(float(res_lossy.generator_power.sum()), 4),
                "shadow_price_range": [
                    round(float(res_lossy.bus_shadow_prices.min()), 6),
                    round(float(res_lossy.bus_shadow_prices.max()), 6),
                ],
                "lmp_uniform": bool(
                    np.allclose(
                        res_lossy.bus_shadow_prices,
                        res_lossy.bus_shadow_prices[0],
                        atol=1e-6,
                    )
                ),
            }

            # Compare
            gen_diff = float(res_lossy.generator_power.sum() - res_lossless.generator_power.sum())
            lmp_diff = float(
                np.max(np.abs(res_lossy.bus_shadow_prices - res_lossless.bus_shadow_prices))
            )
            details["lossy_vs_lossless"] = {
                "total_gen_diff_mw": round(gen_diff, 4),
                "max_lmp_diff": round(lmp_diff, 6),
                "losses_increase_gen": gen_diff > 0.1,
                "lmps_differ": lmp_diff > 1e-6,
            }

            wall_clock = t_lossy
        else:
            wall_clock = t_lossless

        details["wall_clock_seconds"] = round(wall_clock, 6)

        # LMP decomposition check (same as TINY — known absent)
        details["has_lmp_decomposition"] = False
        details["lmp_decomposition_note"] = (
            "GridCal provides bus_shadow_prices (total LMP) but does NOT decompose "
            "into energy, congestion, and loss components."
        )

        # Assessment
        has_lossy = details.get("lossy_dcopf", {}).get("converged", False)
        has_lmp_diff = details.get("lossy_vs_lossless", {}).get("lmps_differ", False)

        if has_lossy and has_lmp_diff:
            status = "qualified_pass"
            details["assessment"] = (
                "Lossy DC OPF works on SMALL network. LMPs vary by bus. "
                "No LMP decomposition (same as TINY)."
            )
        elif has_lossy:
            status = "qualified_pass"
            details["assessment"] = "Loss approximation runs but may not change results."
        else:
            status = "fail"
            errors.append("No lossy DC OPF capability found")

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
