"""
Test C-4: SCUC 24hr on SMALL (ACTIVSg 2000-bus) with HiGHS

Dimension: scalability
Network: SMALL (ACTIVSg2000)
Pass condition: Solves to feasibility. MIP gap and wall-clock time recorded.
    MIP gap tolerance <= 10% on SMALL. Timeout at 600 seconds.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m")

SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600.0,
    "mip_rel_gap": 0.10,  # 10% MIP gap tolerance for SMALL
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

TIMEOUT_SECONDS = 600

# 24-hour load profile (fraction of base load) - typical daily pattern
LOAD_PROFILE = [
    0.67,
    0.63,
    0.60,
    0.59,
    0.59,
    0.60,  # HE1-6 (night)
    0.74,
    0.86,
    0.95,
    0.96,
    0.96,
    0.93,  # HE7-12 (morning ramp)
    0.92,
    0.92,
    0.93,
    0.94,
    0.99,
    1.00,  # HE13-18 (afternoon peak)
    0.96,
    0.91,
    0.83,
    0.73,
    0.63,
    0.60,  # HE19-24 (evening ramp-down)
]


def _load_network_with_costs(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network and set marginal costs from gencost."""
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

    # Parse gencost and set marginal_cost + startup/shutdown costs
    gencost = cf.gencost.values
    workarounds = []
    num_gens = len(net.generators)
    costs_set = 0

    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])

            startup_cost = float(cost_row[1])
            shutdown_cost = float(cost_row[2])
            net.generators.loc[gen_idx, "start_up_cost"] = startup_cost
            net.generators.loc[gen_idx, "shut_down_cost"] = shutdown_cost

            if cost_type == 2:  # Polynomial
                coeffs = cost_row[4 : 4 + n_coeffs]
                if n_coeffs >= 2:
                    c1 = float(coeffs[-2])
                    net.generators.loc[gen_idx, "marginal_cost"] = c1
                    costs_set += 1
                elif n_coeffs == 1:
                    net.generators.loc[gen_idx, "marginal_cost"] = 0.0
                    costs_set += 1
            elif cost_type == 1:  # Piecewise linear
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

    return net, workarounds


def _get_peak_memory_mb():
    """Get peak memory usage in MB using resource module."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024.0  # Linux returns KB
    except Exception:
        return None


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute 24-hour SCUC on 2000-bus network and return structured results.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
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

        _get_peak_memory_mb()

        # 1. Load network with costs
        n, load_workarounds = _load_network_with_costs(network_file)
        results["workarounds"].extend(load_workarounds)

        network_stats = {
            "n_buses": len(n.buses),
            "n_generators": len(n.generators),
            "n_lines": len(n.lines),
            "n_transformers": len(n.transformers),
            "n_loads": len(n.loads),
        }

        # 2. Create 24 hourly snapshots
        snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
        n.set_snapshots(snapshots)

        # 3. Create time-varying load profile
        base_loads = n.loads["p_set"].copy()
        load_profile_series = pd.Series(LOAD_PROFILE, index=snapshots)
        for load_idx in n.loads.index:
            base_p = base_loads[load_idx]
            n.loads_t.p_set[load_idx] = load_profile_series * base_p

        # 4. Set generators as committable with UC parameters
        n.generators["committable"] = True
        n.generators["min_up_time"] = 3
        n.generators["min_down_time"] = 2
        n.generators["ramp_limit_up"] = 0.3
        n.generators["ramp_limit_down"] = 0.3
        n.generators["p_min_pu"] = 0.3

        # Set nominal startup/shutdown costs where missing
        zero_startup = n.generators["start_up_cost"] == 0
        n.generators.loc[zero_startup, "start_up_cost"] = 100.0
        zero_shutdown = n.generators["shut_down_cost"] == 0
        n.generators.loc[zero_shutdown, "shut_down_cost"] = 50.0

        # 5. Solve SCUC
        status = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        elapsed = time.perf_counter() - start

        mem_after = _get_peak_memory_mb()
        peak_memory_mb = mem_after if mem_after else None

        # 6. Check convergence
        # Linopy may report "ok" with "time_limit" — check termination condition
        solver_status = str(status)
        converged = False
        timed_out = elapsed >= TIMEOUT_SECONDS

        # Extract termination condition from status tuple
        term_condition = ""
        if isinstance(status, tuple):
            solver_status = str(status[0])
            term_condition = str(status[1]) if len(status) > 1 else ""
            converged = (
                "ok" in solver_status.lower() or "optimal" in solver_status.lower()
            ) and "time_limit" not in term_condition.lower()
        elif isinstance(status, str):
            converged = "ok" in status.lower() or "optimal" in status.lower()
        else:
            converged = "ok" in str(status).lower() or "optimal" in str(status).lower()

        # Check if objective is finite (inf means no feasible solution found)
        objective_raw = n.objective if hasattr(n, "objective") else None
        objective_finite = objective_raw is not None and np.isfinite(objective_raw)
        if not objective_finite:
            converged = False
        objective = (
            float(objective_raw)
            if objective_raw is not None and np.isfinite(objective_raw)
            else None
        )

        # 7. Extract MIP gap
        mip_gap = None
        try:
            if hasattr(n, "model") and hasattr(n.model, "solver_model"):
                solver_model = n.model.solver_model
                if hasattr(solver_model, "getInfoValue"):
                    gap_val = solver_model.getInfoValue("mip_gap")
                    if gap_val is not None and np.isfinite(gap_val):
                        mip_gap = gap_val
        except Exception:
            pass

        # 8. Extract commitment schedule (if solution exists)
        commitment_stats = {}
        try:
            status_df = n.generators_t.status
            if status_df is not None and len(status_df) > 0 and objective_finite:
                commitment_stats = {
                    "shape": list(status_df.shape),
                    "total_commitments": int(status_df.sum().sum()),
                    "max_simultaneous_online": int(status_df.sum(axis=1).max()),
                    "min_simultaneous_online": int(status_df.sum(axis=1).min()),
                    "generators_always_on": int((status_df.sum(axis=0) == 24).sum()),
                    "generators_never_on": int((status_df.sum(axis=0) == 0).sum()),
                }
        except Exception:
            pass

        # 9. Extract dispatch summary (if solution exists)
        dispatch_stats = {}
        try:
            gen_dispatch = n.generators_t.p
            if gen_dispatch is not None and len(gen_dispatch) > 0 and objective_finite:
                hourly_total = gen_dispatch.sum(axis=1)
                dispatch_stats = {
                    "peak_dispatch_MW": float(hourly_total.max()),
                    "min_dispatch_MW": float(hourly_total.min()),
                    "mean_dispatch_MW": float(hourly_total.mean()),
                }
        except Exception:
            pass

        results["wall_clock_seconds"] = elapsed
        results["details"] = {
            "converged": converged,
            "timed_out": timed_out,
            "solver_status": solver_status,
            "termination_condition": term_condition,
            "solver": SOLVER_NAME,
            "solver_options": SOLVER_OPTIONS,
            "objective": objective,
            "objective_finite": objective_finite,
            "mip_gap": mip_gap,
            "network": network_stats,
            "commitment": commitment_stats,
            "dispatch": dispatch_stats,
            "peak_memory_mb": peak_memory_mb,
            "pypsa_version": pypsa.__version__,
        }

        # Pass condition: solves to feasibility within timeout
        if converged and objective_finite:
            if mip_gap is not None and mip_gap <= 0.10:
                results["status"] = "pass"
            elif mip_gap is None:
                # Solver converged but gap not extractable
                results["status"] = "pass"
                results["workarounds"].append(
                    "MIP gap not extractable from solver model; solver reported optimal/feasible"
                )
            else:
                results["status"] = "qualified_pass"
                results["workarounds"].append(f"MIP gap {mip_gap:.4f} exceeds 10% tolerance")
        elif "time_limit" in term_condition.lower() or timed_out:
            results["status"] = "fail"
            results["errors"].append(
                f"Solver timed out at {TIMEOUT_SECONDS}s. "
                f"MIP gap: {mip_gap if mip_gap else 'unknown'}. "
                f"Feasible solution found: {objective_finite}"
            )
        else:
            results["status"] = "fail"
            results["errors"].append(f"Solver did not converge: {solver_status}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json
    import math

    def _json_safe(obj):
        """Convert non-JSON-serializable values."""
        if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
            return str(obj)
        return str(obj)

    result = run()
    print(json.dumps(result, indent=2, default=_json_safe))
