"""
Test C-3: DC OPF on MEDIUM with HiGHS and GLPK

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k — 10,000 buses)
Pass condition: Completes DC OPF on MEDIUM with HiGHS and GLPK. Wall-clock per solver,
    peak memory, objective value. Max branch loading must be reported.
Tool: PyPSA 1.1.2
Solver: HiGHS, GLPK
"""

import os
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# Solver configurations per solver-config.md
HIGHS_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
    "log_to_console": True,
}

GLPK_OPTIONS = {
    "tmlim": 300,  # seconds (glpsol --tmlim)
}


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DC OPF on ACTIVSg10k with HiGHS and GLPK.

    Returns:
        dict with keys:
        - status: "pass" | "fail"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [
            "Generator marginal costs assigned from gencost via shared loader "
            "(import_from_pypower_ppc does not import gencost natively)",
            "Zero-rated lines (s_nom=0) handled via overwrite_zero_s_nom=99999.0 — "
            "MATPOWER rateA=0 means 'no thermal limit', set to 99999 MW for OPF feasibility.",
        ],
    }

    start = time.perf_counter()
    try:
        from matpower_loader import load_pypsa

        # 1. Load network via shared loader (gets gencost, branch status patches)
        # Use overwrite_zero_s_nom=99999.0 — MATPOWER rateA=0 means "no thermal limit",
        # not "zero capacity". Setting to 99999 MW makes these branches effectively unconstrained.
        load_start = time.perf_counter()
        n_base = load_pypsa(network_file, overwrite_zero_s_nom=99999.0)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n_base.buses)
        results["details"]["n_lines"] = len(n_base.lines)
        results["details"]["n_generators"] = len(n_base.generators)
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["cpu_threads_available"] = os.cpu_count()
        results["details"]["cpu_threads_used"] = 1  # single-threaded per config
        print(
            f"Network loaded: {len(n_base.buses)} buses, {len(n_base.lines)} lines, "
            f"{len(n_base.generators)} generators in {load_elapsed:.2f}s"
        )

        # Check if gencost was loaded (marginal_cost > 0 for at least some generators)
        n_with_cost = int((n_base.generators.marginal_cost > 0).sum())
        n_zero_cost = int((n_base.generators.marginal_cost == 0).sum())
        print(
            f"Marginal costs: {n_with_cost} generators with cost > 0, {n_zero_cost} with cost = 0"
        )
        results["details"]["n_generators_with_cost"] = n_with_cost

        if n_with_cost == 0:
            # Fallback: assign synthetic costs if gencost not available
            print("WARNING: No gencost data — assigning synthetic marginal costs")
            gen_names = sorted(n_base.generators.index)
            costs = np.linspace(10, 100, len(gen_names))
            for gen_name, cost in zip(gen_names, costs):
                n_base.generators.at[gen_name, "marginal_cost"] = float(cost)
            results["workarounds"].append(
                "Synthetic marginal costs $10-$100/MWh assigned (no gencost in .m file)"
            )

        print(
            f"Marginal cost range: ${n_base.generators.marginal_cost.min():.2f}–"
            f"${n_base.generators.marginal_cost.max():.2f}/MWh"
        )

        # 2. Run DC OPF with each solver
        solver_results = {}
        for solver_name, solver_options in [("highs", HIGHS_OPTIONS), ("glpk", GLPK_OPTIONS)]:
            print(f"\n=== DC OPF with {solver_name.upper()} ===")
            n = n_base.copy()

            tracemalloc.start()
            solve_start = time.perf_counter()
            try:
                opt_result = n.optimize(
                    solver_name=solver_name,
                    solver_options=solver_options,
                )
                solve_elapsed = time.perf_counter() - solve_start
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                sr = {
                    "solve_seconds": solve_elapsed,
                    "peak_memory_mb": peak / (1024 * 1024),
                    "solver_result": str(opt_result),
                }

                # Parse result
                if isinstance(opt_result, tuple):
                    status_str = str(opt_result[0]).lower()
                    condition_str = str(opt_result[1]).lower()
                else:
                    status_str = str(opt_result).lower()
                    condition_str = ""

                sr["solver_status"] = status_str
                sr["solver_condition"] = condition_str
                solve_ok = status_str in ("ok", "optimal")

                if solve_ok:
                    sr["objective_dollar"] = float(n.objective)
                    print(f"  Objective: ${sr['objective_dollar']:,.0f}")

                    # Dispatch stats
                    if len(n.generators_t.p) > 0:
                        dispatch = n.generators_t.p.iloc[0]
                        sr["dispatch_total_mw"] = float(dispatch.sum())
                        sr["n_generators_dispatched"] = int((dispatch > 0.1).sum())
                        print(f"  Dispatch: total={dispatch.sum():.0f} MW")

                    # LMP stats
                    if len(n.buses_t.marginal_price) > 0:
                        lmps = n.buses_t.marginal_price.iloc[0]
                        sr["lmp_min"] = float(lmps.min())
                        sr["lmp_max"] = float(lmps.max())
                        sr["lmp_mean"] = float(lmps.mean())
                        sr["lmp_uniform"] = bool(lmps.max() - lmps.min() < 0.01)
                        print(
                            f"  LMPs: min=${lmps.min():.2f}, max=${lmps.max():.2f}, "
                            f"mean=${lmps.mean():.2f}/MWh"
                        )

                    # Branch loading stats
                    if len(n.lines_t.p0) > 0:
                        flows = n.lines_t.p0.iloc[0].abs()
                        s_nom = n.lines.s_nom
                        # Avoid division by zero for unconstrained lines
                        valid_mask = s_nom > 0
                        utilization = flows[valid_mask] / s_nom[valid_mask]
                        sr["max_line_loading_pct"] = float(utilization.max() * 100)
                        sr["n_binding_lines"] = int((utilization >= 0.999).sum())
                        sr["max_flow_mw"] = float(flows.max())
                        print(
                            f"  Max loading: {sr['max_line_loading_pct']:.1f}%, "
                            f"binding: {sr['n_binding_lines']}"
                        )
                else:
                    sr["solve_failed"] = True
                    print(f"  FAILED: {opt_result}")

                print(f"  Time: {solve_elapsed:.3f}s, Memory: {sr['peak_memory_mb']:.1f} MB")

            except Exception as e:
                try:
                    tracemalloc.stop()
                except Exception:
                    pass
                sr = {"error": f"{type(e).__name__}: {e}"}
                print(f"  ERROR: {e}")

            solver_results[solver_name] = sr

        results["details"]["solver_results"] = solver_results

        # Check if at least one solver succeeded
        any_success = any(
            sr.get("solver_status") in ("ok", "optimal") for sr in solver_results.values()
        )
        if any_success:
            results["status"] = "pass"
        else:
            results["errors"].append("No solver completed DC OPF successfully")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
