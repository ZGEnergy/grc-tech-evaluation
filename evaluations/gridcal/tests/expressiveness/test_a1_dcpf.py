"""A-1: DC Power Flow on IEEE 39-bus (TINY) using GridCal/VeraGridEngine."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Execute A-1 DCPF test and return structured results."""
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

        # Configure and run DCPF
        opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)

        t0 = time.perf_counter()
        results = vge.power_flow(grid, options=opts)
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["converged"] = bool(results.converged)

        if not results.converged:
            errors.append("DCPF did not converge")
            return {
                "status": "fail",
                "wall_clock_seconds": wall_clock,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        # Extract structured outputs
        voltage = results.voltage  # complex bus voltages
        va_deg = np.angle(voltage, deg=True)  # voltage angles in degrees
        vm = np.abs(voltage)  # voltage magnitudes (all 1.0 for DC)
        sf = results.Sf  # complex "from" branch flows
        sbus = results.Sbus  # complex bus injections

        details["output_format"] = (
            "numpy arrays + pandas DataFrames via get_bus_df()/get_branch_df()"
        )
        details["voltage_angles_range"] = [
            round(float(va_deg.min()), 4),
            round(float(va_deg.max()), 4),
        ]
        details["vm_all_unity"] = bool(np.allclose(vm, 1.0))
        details["sf_range_mw"] = [round(float(sf.real.min()), 2), round(float(sf.real.max()), 2)]
        details["nodal_injections_available"] = True
        details["sbus_range_mw"] = [
            round(float(sbus.real.min()), 2),
            round(float(sbus.real.max()), 2),
        ]

        # DataFrame access
        bus_df = results.get_bus_df()
        branch_df = results.get_branch_df()
        details["bus_df_columns"] = list(bus_df.columns)
        details["bus_df_shape"] = list(bus_df.shape)
        details["branch_df_columns"] = list(branch_df.columns)
        details["branch_df_shape"] = list(branch_df.shape)

        # Verify DC PF properties: Q flows = 0, losses = 0, Vm = 1.0
        q_flows = sf.imag
        details["q_flows_zero"] = bool(np.allclose(q_flows, 0.0, atol=1e-10))
        losses_real = results.losses.real if hasattr(results, "losses") else None
        if losses_real is not None:
            details["losses_zero"] = bool(np.allclose(losses_real, 0.0, atol=1e-10))

        # Verify power balance: sum of injections ~ 0
        total_injection = sbus.real.sum()
        details["total_injection_mw"] = round(float(total_injection), 6)

        # Solver info
        details["solver"] = "Direct solve (B-inverse method, SolverType.Linear)"
        details["solver_note"] = "GridCal uses SolverType.Linear for DCPF — not called 'DC' in enum"

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
