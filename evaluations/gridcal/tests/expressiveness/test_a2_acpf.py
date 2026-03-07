"""A-2: AC Power Flow (Newton-Raphson) on IEEE 39-bus (TINY) using GridCal/VeraGridEngine."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Execute A-2 ACPF test with convergence protocol."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # Load network
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["branches"] = len(grid.lines) + len(grid.transformers2w)
        details["generators"] = len(grid.generators)

        # ── Attempt 1: Flat start (default initial conditions) ──
        opts = vge.PowerFlowOptions(
            solver_type=SolverType.NR,
            max_iter=100,
            tolerance=1e-6,
            retry_with_other_methods=False,  # disable auto-retry for clean measurement
        )

        t0 = time.perf_counter()
        results = vge.power_flow(grid, options=opts)
        wall_clock = time.perf_counter() - t0

        details["attempt_1"] = {
            "method": "Newton-Raphson (flat start, default Vm0/Va0)",
            "converged": bool(results.converged),
            "error": float(results.error),
            "wall_clock_seconds": round(wall_clock, 6),
        }

        if not results.converged:
            # ── Attempt 2: DC warm start fallback ──
            dc_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
            dc_results = vge.power_flow(grid, options=dc_opts)

            # Set initial voltage from DC solution
            for i, bus in enumerate(grid.buses):
                bus.Va0 = np.angle(dc_results.voltage[i])

            t0 = time.perf_counter()
            results = vge.power_flow(grid, options=opts)
            wall_clock = time.perf_counter() - t0

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
                    "reason": "Used documented API (PowerFlowOptions, bus Va0 attributes)",
                }
            )

        if not results.converged:
            errors.append("ACPF did not converge after flat start and DC warm start")
            return {
                "status": "fail",
                "wall_clock_seconds": wall_clock,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["converged"] = True
        details["convergence_error"] = float(results.error)

        # Extract outputs
        vm = np.abs(results.voltage)
        va_deg = np.angle(results.voltage, deg=True)
        sf = results.Sf
        losses = results.losses

        details["output_format"] = (
            "numpy arrays + pandas DataFrames via get_bus_df()/get_branch_df()"
        )

        # Bus voltage magnitudes and angles
        details["vm_range"] = [round(float(vm.min()), 6), round(float(vm.max()), 6)]
        details["va_range_deg"] = [round(float(va_deg.min()), 4), round(float(va_deg.max()), 4)]

        # Line P/Q flows
        details["pf_range_mw"] = [round(float(sf.real.min()), 2), round(float(sf.real.max()), 2)]
        details["qf_range_mvar"] = [round(float(sf.imag.min()), 2), round(float(sf.imag.max()), 2)]

        # Losses
        details["total_p_loss_mw"] = round(float(losses.real.sum()), 4)
        details["total_q_loss_mvar"] = round(float(losses.imag.sum()), 4)
        details["losses_nonzero"] = bool(np.any(np.abs(losses.real) > 1e-6))

        # DataFrame access
        bus_df = results.get_bus_df()
        branch_df = results.get_branch_df()
        details["bus_df_columns"] = list(bus_df.columns)
        details["bus_df_shape"] = list(bus_df.shape)
        details["branch_df_columns"] = list(branch_df.columns)
        details["branch_df_shape"] = list(branch_df.shape)

        # Solver notes
        details["solver"] = "GridCal built-in Newton-Raphson (not Ipopt)"
        details["solver_note"] = (
            "GridCal uses its own NR implementation for ACPF, not Ipopt. "
            "Ipopt is not used for power flow — only the AC OPF uses a custom interior-point solver. "
            "This is documented behavior."
        )

        status = "pass"

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
