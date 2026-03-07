"""
Test C-8: SCOPF Scale Test

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k)
Pass condition: SCOPF with 500 monitored contingencies solves or times out gracefully.
    Wall-clock, objective, and memory recorded.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import json
import math
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600.0,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

NUM_CONTINGENCIES = 500
TIMEOUT_SECONDS = 600


def _load_network_with_costs(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network and manually set marginal costs."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)

    gencost = cf.gencost.values
    workarounds = []
    num_gens = len(net.generators)
    costs_set = 0
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])
            if cost_type == 2:
                coeffs = cost_row[4 : 4 + n_coeffs]
                if n_coeffs >= 2:
                    c1 = float(coeffs[-2])
                    net.generators.loc[gen_idx, "marginal_cost"] = c1
                    costs_set += 1
                elif n_coeffs == 1:
                    net.generators.loc[gen_idx, "marginal_cost"] = 0.0
                    costs_set += 1
            elif cost_type == 1:
                n_pairs = int(cost_row[3])
                pairs = cost_row[4 : 4 + 2 * n_pairs].reshape(-1, 2)
                if len(pairs) >= 2:
                    dp = pairs[-1, 0] - pairs[0, 0]
                    dc = pairs[-1, 1] - pairs[0, 1]
                    mc = dc / dp if dp > 0 else 0.0
                    net.generators.loc[gen_idx, "marginal_cost"] = mc
                    costs_set += 1

    if costs_set > 0:
        workarounds.append(
            f"Manually set marginal_cost on {costs_set}/{num_gens} generators "
            "from gencost data (PPC importer does not import gencost)"
        )

    # Fix zero s_nom branches
    zero_s_nom_lines = net.lines["s_nom"] == 0
    if zero_s_nom_lines.any():
        net.lines.loc[zero_s_nom_lines, "s_nom"] = 9999.0
        workarounds.append(
            f"Set s_nom=9999 on {zero_s_nom_lines.sum()} lines with zero thermal rating"
        )

    zero_s_nom_xfmr = net.transformers["s_nom"] == 0
    if zero_s_nom_xfmr.any():
        net.transformers.loc[zero_s_nom_xfmr, "s_nom"] = 9999.0
        workarounds.append(
            f"Set s_nom=9999 on {zero_s_nom_xfmr.sum()} transformers with zero rating"
        )

    zero_x_lines = net.lines["x"] == 0
    if zero_x_lines.any():
        net.lines.loc[zero_x_lines, "x"] = 0.0001
        workarounds.append(f"Set x=0.0001 on {zero_x_lines.sum()} lines with zero reactance")

    zero_x_xfmr = net.transformers["x"] == 0
    if zero_x_xfmr.any():
        net.transformers.loc[zero_x_xfmr, "x"] = 0.0001
        workarounds.append(f"Set x=0.0001 on {zero_x_xfmr.sum()} transformers with zero reactance")

    return net, workarounds


def _get_peak_memory_mb():
    """Get peak memory usage in MB using resource module."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024.0
    except Exception:
        return None


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute SCOPF with 500 contingencies on 10k-bus network."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pypsa

        mem_before = _get_peak_memory_mb()

        # 1. Load network with costs
        n, load_workarounds = _load_network_with_costs(network_file)
        results["workarounds"].extend(load_workarounds)

        network_stats = {
            "n_buses": len(n.buses),
            "n_generators": len(n.generators),
            "n_lines": len(n.lines),
            "n_transformers": len(n.transformers),
        }

        # 2. Select 500 monitored contingencies (first 500 lines by index)
        all_lines = n.lines.index.tolist()
        monitored = all_lines[:NUM_CONTINGENCIES]
        actual_contingencies = len(monitored)

        results["details"]["total_lines"] = len(all_lines)
        results["details"]["monitored_contingencies"] = actual_contingencies

        # 3. First solve baseline DCOPF for comparison
        n_baseline = n.copy()
        baseline_status = n_baseline.optimize(
            solver_name=SOLVER_NAME, solver_options=SOLVER_OPTIONS
        )
        baseline_converged = (
            "ok" in str(baseline_status).lower() or "optimal" in str(baseline_status).lower()
        )
        baseline_objective = (
            float(n_baseline.objective) if hasattr(n_baseline, "objective") else None
        )

        results["details"]["baseline_dcopf"] = {
            "converged": baseline_converged,
            "objective": baseline_objective,
            "status": str(baseline_status),
        }

        # 4. Solve SCOPF with rating relaxation escalation
        scopf_converged = False
        scopf_status = None
        rating_scale = 1.0

        for scale_factor in [1.0, 1.5, 2.0]:
            if time.perf_counter() - start > TIMEOUT_SECONDS:
                results["errors"].append("Timeout before SCOPF solve attempt")
                break

            n_try = n.copy()
            if scale_factor > 1.0:
                n_try.lines["s_nom"] = n.lines["s_nom"] * scale_factor
                results["workarounds"].append(
                    f"Scaled thermal ratings to {scale_factor * 100:.0f}% "
                    "due to infeasibility at original ratings"
                )

            solve_start = time.perf_counter()
            try:
                scopf_status = n_try.optimize.optimize_security_constrained(
                    branch_outages=monitored,
                    solver_name=SOLVER_NAME,
                    solver_options=SOLVER_OPTIONS,
                )
                solve_elapsed = time.perf_counter() - solve_start

                status_str = str(scopf_status)
                scopf_converged = "ok" in status_str.lower() or "optimal" in status_str.lower()

                if scopf_converged:
                    rating_scale = scale_factor
                    results["details"]["scopf_solve_time_seconds"] = solve_elapsed
                    break
                else:
                    results["details"][f"scopf_status_at_{scale_factor}x"] = status_str

            except Exception as e:
                solve_elapsed = time.perf_counter() - solve_start
                results["details"][f"scopf_error_at_{scale_factor}x"] = str(e)
                if scale_factor == 2.0:
                    results["errors"].append(f"SCOPF failed even at 200% rating: {e}")

        mem_after = _get_peak_memory_mb()
        total_elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = total_elapsed

        # 5. Extract SCOPF results
        if scopf_converged:
            scopf_objective = float(n_try.objective) if hasattr(n_try, "objective") else None

            dispatch_stats = {}
            gen_dispatch = n_try.generators_t.p
            if gen_dispatch is not None and len(gen_dispatch) > 0:
                dispatch = gen_dispatch.iloc[0]
                dispatch_stats = {
                    "total_dispatch_MW": float(dispatch.sum()),
                    "min_MW": float(dispatch.min()),
                    "max_MW": float(dispatch.max()),
                }

            cost_increase = None
            cost_increase_pct = None
            if baseline_objective and scopf_objective:
                cost_increase = scopf_objective - baseline_objective
                cost_increase_pct = (
                    cost_increase / baseline_objective * 100 if baseline_objective > 0 else 0
                )

            results["details"]["scopf"] = {
                "converged": True,
                "objective": scopf_objective,
                "status": str(scopf_status),
                "rating_scale_used": rating_scale,
                "dispatch": dispatch_stats,
                "cost_increase_vs_dcopf": cost_increase,
                "cost_increase_pct": cost_increase_pct,
            }
            results["status"] = "pass"
        else:
            timed_out = total_elapsed >= TIMEOUT_SECONDS
            results["details"]["scopf"] = {
                "converged": False,
                "status": str(scopf_status),
                "timed_out": timed_out,
            }
            if timed_out:
                results["status"] = "fail"
                results["errors"].append(
                    f"SCOPF timed out at {TIMEOUT_SECONDS}s with {actual_contingencies} contingencies"
                )
            else:
                results["status"] = "fail"

        results["details"]["network"] = network_stats
        results["details"]["peak_memory_mb"] = mem_after
        results["details"]["mem_before_mb"] = mem_before
        results["details"]["pypsa_version"] = pypsa.__version__
        results["details"]["api_method"] = "n.optimize.optimize_security_constrained()"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":

    def _json_safe(obj):
        if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
            return str(obj)
        return str(obj)

    result = run()
    print(json.dumps(result, indent=2, default=_json_safe))
