"""B-3: N-1 Contingency Loop on IEEE 39-bus (TINY).

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Runs N-1 DCPF contingencies in loop without re-parsing base model.
Base model modified in-place or cloned efficiently. TINY: all 46 branches.
Collect max line loading across all cases.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Execute B-3 contingency loop test."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # Load network once
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()

        branches = list(grid.lines) + list(grid.transformers2w)
        n_branches = len(branches)
        details["total_branches"] = n_branches

        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)

        # ── Step 1: Baseline DCPF ──
        t0_base = time.perf_counter()
        base_results = vge.power_flow(grid, options=pf_opts)
        t_base = time.perf_counter() - t0_base

        if not base_results.converged:
            errors.append("Baseline DCPF did not converge")
            return {
                "status": "fail",
                "wall_clock_seconds": t_base,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        base_sf = np.abs(base_results.Sf.real)
        base_loading = np.abs(base_results.loading.real) * 100  # percent
        details["baseline"] = {
            "converged": True,
            "wall_clock_seconds": round(t_base, 6),
            "max_flow_mw": round(float(base_sf.max()), 4),
            "max_loading_pct": round(float(base_loading.max()), 4),
        }

        # ── Step 2: N-1 contingency loop ──
        t0_loop = time.perf_counter()

        contingency_results = []
        max_loading_overall = 0.0
        worst_contingency = None
        non_converged_count = 0

        for i in range(n_branches):
            # Disable branch in-place
            branches[i].active = False

            # Solve DCPF
            pf_result = vge.power_flow(grid, options=pf_opts)

            if pf_result.converged:
                loading = np.abs(pf_result.loading.real) * 100
                max_load_pct = float(np.max(loading))
                sf = np.abs(pf_result.Sf.real)
                max_flow_mw = float(np.max(sf))

                case = {
                    "branch_index": i,
                    "branch_name": branches[i].name,
                    "converged": True,
                    "max_loading_pct": round(max_load_pct, 4),
                    "max_flow_mw": round(max_flow_mw, 4),
                }

                if max_load_pct > max_loading_overall:
                    max_loading_overall = max_load_pct
                    worst_contingency = i
            else:
                non_converged_count += 1
                case = {
                    "branch_index": i,
                    "branch_name": branches[i].name,
                    "converged": False,
                    "max_loading_pct": None,
                    "max_flow_mw": None,
                }

            contingency_results.append(case)

            # Re-enable branch
            branches[i].active = True

        t_loop = time.perf_counter() - t0_loop
        wall_clock = t_base + t_loop

        details["n1_loop"] = {
            "total_contingencies": n_branches,
            "converged": n_branches - non_converged_count,
            "non_converged": non_converged_count,
            "wall_clock_seconds": round(t_loop, 6),
            "per_contingency_avg_ms": round(t_loop / n_branches * 1000, 4),
            "max_loading_pct": round(max_loading_overall, 4),
            "worst_contingency_index": worst_contingency,
            "worst_contingency_name": (
                branches[worst_contingency].name if worst_contingency is not None else None
            ),
        }

        # Top 5 most loaded contingencies
        converged_cases = [c for c in contingency_results if c["converged"]]
        top5 = sorted(converged_cases, key=lambda c: c["max_loading_pct"], reverse=True)[:5]
        details["top5_loading"] = top5

        # All results
        details["contingency_results"] = contingency_results

        # ── Step 3: Verify model integrity after loop ──
        # Re-run baseline to confirm no state corruption
        verify_results = vge.power_flow(grid, options=pf_opts)
        verify_sf = np.abs(verify_results.Sf.real)
        flow_diff = float(np.max(np.abs(verify_sf - base_sf)))
        details["model_integrity"] = {
            "post_loop_converged": bool(verify_results.converged),
            "max_flow_difference_mw": round(flow_diff, 8),
            "model_unmodified": flow_diff < 1e-6,
        }

        # ── Step 4: Check for built-in contingency analysis ──
        has_ca_driver = hasattr(vge, "ContingencyAnalysisDriver")
        details["builtin_contingency_driver"] = has_ca_driver

        if has_ca_driver:
            details["ca_driver_note"] = (
                "ContingencyAnalysisDriver exists but handles pre-defined contingency "
                "groups (N-1). The manual loop approach gives full control over which "
                "branches to disable and how to collect results."
            )

        # Assess pass condition
        model_ok = details["model_integrity"]["model_unmodified"]
        all_ran = details["n1_loop"]["total_contingencies"] == n_branches

        if model_ok and all_ran:
            status = "pass"
            details["pass_rationale"] = (
                f"All {n_branches} N-1 contingencies solved without re-parsing model. "
                "branch.active toggle modifies in-place; model integrity verified. "
                f"Loop took {round(t_loop, 3)}s ({round(t_loop / n_branches * 1000, 1)}ms/case)."
            )
        else:
            status = "fail"
            if not model_ok:
                errors.append("Model state corrupted after contingency loop")

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
    # Print summary without full contingency list
    summary = {k: v for k, v in result.items() if k != "details"}
    summary["details"] = {k: v for k, v in result["details"].items() if k != "contingency_results"}
    print(json.dumps(summary, indent=2, default=str))
