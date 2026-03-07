"""C-9: PTDF Scale on ACTIVSg10k (MEDIUM, 10000 buses).

Dimension: scalability
Network: MEDIUM
Pass condition: Compute PTDF matrix on 10k-bus network within 600s.
Verify dimensions and PTDF-predicted flows match DCPF.
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute C-9 PTDF scalability test on MEDIUM network."""
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
        grid = vge.open_file(NETWORK_FILE)
        n_bus = grid.get_bus_number()
        branches = list(grid.lines) + list(grid.transformers2w)
        n_branch = len(branches)
        details["buses"] = n_bus
        details["branches"] = n_branch

        # ── Compute PTDF ──
        tracemalloc.start()
        t0 = time.perf_counter()
        la_results = vge.linear_power_flow(grid)
        wall_clock = time.perf_counter() - t0
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["peak_memory_mb"] = round(peak_mem / (1024 * 1024), 2)

        ptdf = la_results.PTDF
        details["ptdf_shape"] = list(ptdf.shape) if hasattr(ptdf, "shape") else str(ptdf)[:100]
        details["ptdf_dtype"] = str(ptdf.dtype) if hasattr(ptdf, "dtype") else None

        # Verify dimensions
        expected_shape = (n_branch, n_bus)
        actual_shape = tuple(ptdf.shape)
        dims_ok = actual_shape == expected_shape
        details["expected_shape"] = list(expected_shape)
        details["actual_shape"] = list(actual_shape)
        details["dimensions_correct"] = dims_ok

        if not dims_ok:
            errors.append(
                f"PTDF dimensions mismatch: expected {expected_shape}, got {actual_shape}"
            )

        # Memory footprint
        ptdf_size_mb = ptdf.nbytes / (1024 * 1024) if hasattr(ptdf, "nbytes") else None
        details["ptdf_size_mb"] = round(ptdf_size_mb, 2) if ptdf_size_mb else None

        # LODF availability
        if hasattr(la_results, "LODF") and la_results.LODF is not None:
            lodf = la_results.LODF
            details["lodf_shape"] = list(lodf.shape) if hasattr(lodf, "shape") else str(lodf)
            details["lodf_available"] = True
        else:
            details["lodf_available"] = False

        # ── Run DCPF for validation ──
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        pf_results = vge.power_flow(grid, options=pf_opts)

        if not pf_results.converged:
            errors.append("DCPF did not converge for PTDF validation")
            return {
                "status": "fail",
                "wall_clock_seconds": wall_clock,
                "peak_memory_mb": details["peak_memory_mb"],
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        dcpf_flows = pf_results.Sf.real
        sbus = pf_results.Sbus.real

        # Compare LA flows vs DCPF
        la_flows = (
            la_results.Sf.real if hasattr(la_results, "Sf") and la_results.Sf is not None else None
        )

        if la_flows is not None:
            la_diff = np.abs(la_flows - dcpf_flows)
            la_max_diff = float(np.max(la_diff))
            details["la_vs_dcpf_max_diff"] = round(la_max_diff, 10)
            max_diff = la_max_diff
        else:
            ptdf_predicted = ptdf @ sbus
            flow_diff = np.abs(ptdf_predicted - dcpf_flows)
            max_diff = float(np.max(flow_diff))
            details["ptdf_sbus_vs_dcpf_max_diff"] = round(max_diff, 10)

        details["flow_match_tolerance"] = 1e-6
        details["flow_within_tolerance"] = max_diff < 1e-6

        # PTDF statistics
        details["ptdf_stats"] = {
            "min": round(float(ptdf.min()), 8),
            "max": round(float(ptdf.max()), 8),
            "nonzero_fraction": round(float(np.count_nonzero(ptdf)) / ptdf.size, 4),
        }

        details["solver"] = "Direct (linear_power_flow)"

        if dims_ok and max_diff < 1e-6:
            status = "pass"
        elif dims_ok and max_diff < 1e-3:
            status = "qualified_pass"
        else:
            status = "fail"

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
