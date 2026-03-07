"""A-10: Lossy DC OPF with LMP Decomposition on IEEE 39-bus (TINY)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Attempt lossy DC OPF and LMP decomposition."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")

        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)
        branches = list(grid.lines) + list(grid.transformers2w)
        details["branches"] = len(branches)

        # ── Check 1: Does OPF have loss-related options? ──
        opts = vge.OptimalPowerFlowOptions()
        loss_attrs = {}
        for attr in dir(opts):
            if any(kw in attr.lower() for kw in ["loss", "resist", "lmp", "decomp"]):
                try:
                    loss_attrs[attr] = str(getattr(opts, attr))
                except Exception:
                    loss_attrs[attr] = "<unreadable>"
        details["opf_loss_options"] = loss_attrs

        # ── Step 1: Standard (lossless) DC OPF ──
        opts_lossless = vge.OptimalPowerFlowOptions()
        opts_lossless.mip_solver = MIPSolvers.HIGHS

        t0 = time.perf_counter()
        res_lossless = vge.linear_opf(grid, options=opts_lossless)
        t_lossless = time.perf_counter() - t0

        details["lossless_dcopf"] = {
            "converged": bool(res_lossless.converged),
            "wall_clock_seconds": round(t_lossless, 6),
            "total_gen_mw": round(float(res_lossless.generator_power.sum()), 4),
            "shadow_prices": [round(float(x), 6) for x in res_lossless.bus_shadow_prices],
            "shadow_price_range": [
                round(float(res_lossless.bus_shadow_prices.min()), 6),
                round(float(res_lossless.bus_shadow_prices.max()), 6),
            ],
        }

        # ── Step 2: Try lossy DC OPF (add_losses_approximation or similar) ──
        grid2 = vge.open_file(NETWORK_FILE)
        opts_lossy = vge.OptimalPowerFlowOptions()
        opts_lossy.mip_solver = MIPSolvers.HIGHS

        # Try to enable loss approximation
        lossy_enabled = False
        if hasattr(opts_lossy, "add_losses_approximation"):
            opts_lossy.add_losses_approximation = True
            lossy_enabled = True
            details["add_losses_approximation"] = True
        elif hasattr(opts_lossy, "consider_losses"):
            opts_lossy.consider_losses = True
            lossy_enabled = True
            details["consider_losses"] = True
        else:
            # Search for any loss-related flag
            for attr in dir(opts_lossy):
                if "loss" in attr.lower() and not attr.startswith("_"):
                    details[f"found_loss_attr_{attr}"] = str(getattr(opts_lossy, attr, "N/A"))

        if lossy_enabled:
            try:
                t0 = time.perf_counter()
                res_lossy = vge.linear_opf(grid2, options=opts_lossy)
                t_lossy = time.perf_counter() - t0

                details["lossy_dcopf"] = {
                    "converged": bool(res_lossy.converged),
                    "wall_clock_seconds": round(t_lossy, 6),
                    "total_gen_mw": round(float(res_lossy.generator_power.sum()), 4),
                    "shadow_prices": [round(float(x), 6) for x in res_lossy.bus_shadow_prices],
                    "shadow_price_range": [
                        round(float(res_lossy.bus_shadow_prices.min()), 6),
                        round(float(res_lossy.bus_shadow_prices.max()), 6),
                    ],
                }

                # Compare lossless vs lossy
                gen_diff = float(
                    res_lossy.generator_power.sum() - res_lossless.generator_power.sum()
                )
                lmp_diff = float(
                    np.max(np.abs(res_lossy.bus_shadow_prices - res_lossless.bus_shadow_prices))
                )
                details["lossy_vs_lossless"] = {
                    "total_gen_diff_mw": round(gen_diff, 4),
                    "max_lmp_diff": round(lmp_diff, 6),
                    "losses_increase_gen": gen_diff > 0.1,
                    "lmps_differ": lmp_diff > 1e-6,
                }

            except Exception as e:
                details["lossy_dcopf_error"] = str(e)
                details["lossy_dcopf_traceback"] = __import__("traceback").format_exc()
        else:
            details["lossy_dcopf_note"] = (
                "No loss approximation option found in OptimalPowerFlowOptions. "
                "GridCal's linear_opf appears to be strictly lossless DC OPF."
            )

        # ── Step 3: Check for LMP decomposition ──
        lmp_decomp_attrs = {}
        if res_lossless.converged:
            for attr in dir(res_lossless):
                if any(
                    kw in attr.lower()
                    for kw in [
                        "lmp",
                        "congestion",
                        "loss_component",
                        "energy_component",
                        "marginal",
                        "decomp",
                        "shadow",
                    ]
                ):
                    try:
                        val = getattr(res_lossless, attr)
                        if callable(val):
                            lmp_decomp_attrs[attr] = "<method>"
                        elif hasattr(val, "shape"):
                            lmp_decomp_attrs[attr] = f"array shape={val.shape}"
                        else:
                            lmp_decomp_attrs[attr] = str(val)
                    except Exception:
                        lmp_decomp_attrs[attr] = "<error>"
        details["lmp_decomposition_attrs"] = lmp_decomp_attrs

        has_lmp_decomp = any(
            kw in attr.lower()
            for attr in lmp_decomp_attrs
            for kw in ["congestion", "loss_component", "energy_component"]
        )
        details["has_lmp_decomposition"] = has_lmp_decomp

        if not has_lmp_decomp:
            details["lmp_decomposition_note"] = (
                "GridCal provides bus_shadow_prices (total LMP) but does NOT decompose "
                "into energy, congestion, and loss components. No built-in LMP decomposition."
            )

        # ── Step 4: Check per-line congestion rent ──
        congestion_rent_attrs = {}
        for attr in dir(res_lossless):
            if any(kw in attr.lower() for kw in ["rent", "revenue", "surplus", "congestion_cost"]):
                try:
                    congestion_rent_attrs[attr] = str(getattr(res_lossless, attr))
                except Exception:
                    congestion_rent_attrs[attr] = "<error>"
        details["congestion_rent_attrs"] = congestion_rent_attrs
        details["has_congestion_rent"] = len(congestion_rent_attrs) > 0

        if not congestion_rent_attrs:
            details["congestion_rent_note"] = (
                "No built-in per-line congestion rent calculation. "
                "Could be computed manually from shadow prices and branch flows."
            )

        # ── Assessment ──
        has_lossy = details.get("lossy_dcopf", {}).get("converged", False)
        has_lmp_diff = details.get("lossy_vs_lossless", {}).get("lmps_differ", False)

        if has_lossy and has_lmp_diff and has_lmp_decomp:
            status = "pass"
        elif has_lossy and has_lmp_diff:
            status = "qualified_pass"
            details["assessment"] = (
                "Lossy DC OPF works and produces different LMPs, "
                "but LMP decomposition is not built-in."
            )
        elif has_lossy:
            status = "qualified_pass"
            details["assessment"] = (
                "Loss approximation option exists but may not change results. No LMP decomposition."
            )
        else:
            status = "fail"
            errors.append("No lossy DC OPF capability or LMP decomposition found")
            details["assessment"] = (
                "GridCal's linear_opf is strictly lossless. No loss approximation option found. "
                "No LMP decomposition into energy/congestion/loss components. "
                "No per-line congestion rent calculation."
            )

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"

    return {
        "status": status,
        "wall_clock_seconds": details.get("lossy_dcopf", {}).get(
            "wall_clock_seconds",
            details.get("lossless_dcopf", {}).get("wall_clock_seconds", 0.0),
        ),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
