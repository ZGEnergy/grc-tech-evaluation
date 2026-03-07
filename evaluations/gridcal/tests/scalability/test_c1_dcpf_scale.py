"""C-1: DCPF Scale on ACTIVSg10k (MEDIUM, 10000 buses).

Dimension: scalability
Network: MEDIUM
Pass condition: DCPF solves on 10k-bus network within 600s.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute C-1 DCPF scalability test on MEDIUM network."""
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

        # Configure DCPF
        opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)

        # Run with memory tracking
        tracemalloc.start()
        t0 = time.perf_counter()
        results = vge.power_flow(grid, options=opts)
        wall_clock = time.perf_counter() - t0
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["peak_memory_mb"] = round(peak_mem / (1024 * 1024), 2)
        details["converged"] = bool(results.converged)

        if not results.converged:
            errors.append("DCPF did not converge on MEDIUM network")
            return {
                "status": "fail",
                "wall_clock_seconds": wall_clock,
                "peak_memory_mb": details["peak_memory_mb"],
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        # Extract key outputs
        voltage = results.voltage
        va_deg = np.angle(voltage, deg=True)
        sf = results.Sf

        details["voltage_angles_range"] = [
            round(float(va_deg.min()), 4),
            round(float(va_deg.max()), 4),
        ]
        details["sf_range_mw"] = [
            round(float(sf.real.min()), 2),
            round(float(sf.real.max()), 2),
        ]
        details["solver"] = "Direct (SolverType.Linear)"

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
