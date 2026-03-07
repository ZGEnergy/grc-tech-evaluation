"""C-2: ACPF Scale on ACTIVSg10k (MEDIUM, 10000 buses).

Dimension: scalability
Network: MEDIUM
Pass condition: ACPF converges on 10k-bus network within 600s.
Follows convergence protocol: flat start -> DC warm start -> auto-retry.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute C-2 ACPF scalability test on MEDIUM network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "case_ACTIVSg10k (MEDIUM, 10000 buses)"

        # Load network
        t_load_0 = time.perf_counter()
        grid = vge.open_file(NETWORK_FILE)
        t_load = time.perf_counter() - t_load_0
        details["load_time_seconds"] = round(t_load, 6)
        details["buses"] = grid.get_bus_number()
        details["branches"] = len(grid.lines) + len(grid.transformers2w)
        details["generators"] = len(grid.generators)

        # ── Attempt 1: Flat start NR ──
        opts = vge.PowerFlowOptions(
            solver_type=SolverType.NR,
            max_iter=100,
            tolerance=1e-6,
            retry_with_other_methods=False,
        )

        tracemalloc.start()
        t0 = time.perf_counter()
        results = vge.power_flow(grid, options=opts)
        wall_clock = time.perf_counter() - t0
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        details["attempt_1"] = {
            "method": "Newton-Raphson (flat start)",
            "converged": bool(results.converged),
            "error": float(results.error),
            "wall_clock_seconds": round(wall_clock, 6),
        }

        if not results.converged:
            # ── Attempt 2: DC warm start ──
            dc_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
            dc_results = vge.power_flow(grid, options=dc_opts)

            for i, bus in enumerate(grid.buses):
                bus.Va0 = np.angle(dc_results.voltage[i])

            tracemalloc.start()
            t0 = time.perf_counter()
            results = vge.power_flow(grid, options=opts)
            wall_clock = time.perf_counter() - t0
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            details["attempt_2"] = {
                "method": "Newton-Raphson (DC warm start)",
                "converged": bool(results.converged),
                "error": float(results.error),
                "wall_clock_seconds": round(wall_clock, 6),
            }

            workarounds.append(
                {
                    "description": "DC warm start fallback for NR convergence",
                    "class": "stable",
                }
            )

        if not results.converged:
            # ── Attempt 3: auto-retry ──
            opts3 = vge.PowerFlowOptions(
                solver_type=SolverType.NR,
                max_iter=200,
                tolerance=1e-6,
                retry_with_other_methods=True,
            )
            tracemalloc.start()
            t0 = time.perf_counter()
            results = vge.power_flow(grid, options=opts3)
            wall_clock = time.perf_counter() - t0
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            details["attempt_3"] = {
                "method": "Newton-Raphson (auto-retry, 200 iter)",
                "converged": bool(results.converged),
                "error": float(results.error),
                "wall_clock_seconds": round(wall_clock, 6),
            }

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["peak_memory_mb"] = round(peak_mem / (1024 * 1024), 2)
        details["converged"] = bool(results.converged)

        if not results.converged:
            errors.append("ACPF did not converge after all attempts on MEDIUM network")
            return {
                "status": "fail",
                "wall_clock_seconds": wall_clock,
                "peak_memory_mb": details["peak_memory_mb"],
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        details["convergence_error"] = float(results.error)

        # Extract key outputs
        vm = np.abs(results.voltage)
        va_deg = np.angle(results.voltage, deg=True)
        sf = results.Sf
        losses = results.losses

        details["vm_range"] = [round(float(vm.min()), 6), round(float(vm.max()), 6)]
        details["va_range_deg"] = [round(float(va_deg.min()), 4), round(float(va_deg.max()), 4)]
        details["pf_range_mw"] = [round(float(sf.real.min()), 2), round(float(sf.real.max()), 2)]
        details["total_p_loss_mw"] = round(float(losses.real.sum()), 4)
        details["losses_nonzero"] = bool(np.any(np.abs(losses.real) > 1e-6))
        details["solver"] = "GridCal built-in Newton-Raphson"

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
        "peak_memory_mb": details.get("peak_memory_mb"),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
