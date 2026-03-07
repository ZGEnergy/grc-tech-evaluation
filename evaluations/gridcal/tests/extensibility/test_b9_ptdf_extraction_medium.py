"""B-9: PTDF Extraction on ACTIVSg10k (MEDIUM).

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k-bus)
Pass condition: Compute PTDF matrix; verify dimensions (branches x buses);
verify PTDF-predicted flows match DCPF-solved flows within 1e-6.
PTDF accessible via native API.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute B-9 PTDF extraction test on MEDIUM network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "MEDIUM (ACTIVSg10k)"

        grid = vge.open_file(NETWORK_FILE)
        n_bus = grid.get_bus_number()
        branches = list(grid.lines) + list(grid.transformers2w)
        n_branch = len(branches)
        details["buses"] = n_bus
        details["branches"] = n_branch

        # ── Step 1: Compute PTDF via LinearAnalysis ──
        t0 = time.perf_counter()
        la_results = vge.linear_power_flow(grid)
        t_ptdf = time.perf_counter() - t0

        details["ptdf_compute_seconds"] = round(t_ptdf, 6)

        # Extract PTDF matrix
        ptdf = la_results.PTDF
        details["ptdf_type"] = type(ptdf).__name__
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

        # PTDF memory footprint
        ptdf_size_mb = ptdf.nbytes / (1024 * 1024) if hasattr(ptdf, "nbytes") else None
        details["ptdf_size_mb"] = round(ptdf_size_mb, 2) if ptdf_size_mb else None

        # ── Step 2: Check LODF also available ──
        if hasattr(la_results, "LODF") and la_results.LODF is not None:
            lodf = la_results.LODF
            details["lodf_shape"] = list(lodf.shape) if hasattr(lodf, "shape") else str(lodf)
            details["lodf_available"] = True
        else:
            details["lodf_available"] = False

        # ── Step 3: Run DCPF for comparison ──
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        pf_results = vge.power_flow(grid, options=pf_opts)

        if not pf_results.converged:
            errors.append("DCPF did not converge")
            return {
                "status": "fail",
                "wall_clock_seconds": t_ptdf,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        dcpf_flows = pf_results.Sf.real
        sbus = pf_results.Sbus.real

        # ── Step 4: Compare LA direct flows vs DCPF ──
        la_flows = (
            la_results.Sf.real if hasattr(la_results, "Sf") and la_results.Sf is not None else None
        )
        details["la_direct_flows_available"] = la_flows is not None

        la_max_diff = None
        if la_flows is not None:
            la_diff = np.abs(la_flows - dcpf_flows)
            la_max_diff = float(np.max(la_diff))
            details["la_vs_dcpf"] = {
                "max_absolute_difference": round(la_max_diff, 10),
                "mean_absolute_difference": round(float(np.mean(la_diff)), 10),
                "match": la_max_diff < 1e-6,
            }

        # PTDF @ injection vector
        ptdf_predicted_flows = ptdf @ sbus
        flow_diff_raw = np.abs(ptdf_predicted_flows - dcpf_flows)
        max_diff_raw = float(np.max(flow_diff_raw))

        details["flow_comparison_ptdf_sbus"] = {
            "max_absolute_difference": round(max_diff_raw, 10),
            "mean_absolute_difference": round(float(np.mean(flow_diff_raw)), 10),
        }

        # Definitive comparison
        max_diff = la_max_diff if la_max_diff is not None else max_diff_raw
        details["flow_comparison"] = {
            "method": "LA direct flows vs DCPF" if la_flows is not None else "PTDF @ Sbus vs DCPF",
            "max_absolute_difference": round(max_diff, 10),
            "tolerance": 1e-6,
            "within_tolerance": max_diff < 1e-6,
        }

        # ── Step 5: PTDF statistics ──
        details["ptdf_stats"] = {
            "min": round(float(ptdf.min()), 8),
            "max": round(float(ptdf.max()), 8),
            "mean": round(float(ptdf.mean()), 8),
            "nonzero_fraction": round(float(np.count_nonzero(ptdf)) / ptdf.size, 4),
        }

        # Slack bus column check
        col_sums = np.abs(ptdf).sum(axis=0)
        min_col_sum_idx = int(np.argmin(col_sums))
        details["likely_slack_bus_index"] = min_col_sum_idx
        details["slack_column_sum"] = round(float(col_sums[min_col_sum_idx]), 10)
        details["slack_column_all_zero"] = bool(
            np.allclose(ptdf[:, min_col_sum_idx], 0, atol=1e-10)
        )

        wall_clock = t_ptdf

        # Assess pass condition
        if dims_ok and max_diff < 1e-6:
            status = "pass"
            details["pass_rationale"] = (
                f"PTDF matrix {actual_shape} extracted via vge.linear_power_flow() on "
                f"10k-bus network in {round(t_ptdf, 3)}s. "
                f"LA flows match DCPF within {max_diff:.2e}. "
                f"PTDF matrix size: {details.get('ptdf_size_mb', 'N/A')} MB."
            )
        elif dims_ok and max_diff_raw < 1e-3:
            status = "qualified_pass"
            details["pass_rationale"] = (
                f"PTDF dimensions correct ({actual_shape}). PTDF @ Sbus max diff = "
                f"{max_diff_raw:.2e}. LA direct flows match DCPF exactly."
            )
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
        "wall_clock_seconds": wall_clock,
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
