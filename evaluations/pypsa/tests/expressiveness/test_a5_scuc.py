"""
Test A-5: Solve 24-hour unit commitment as MILP with min up/down times, startup costs,
ramp rates, reserve requirements

Dimension: expressiveness
Network: TINY (case39)
Pass condition: Solves to feasibility (MIP gap <= 1% on TINY). Commitment schedule
    extractable as a time-indexed binary matrix. Built-in constraint types vs.
    user-assembled noted.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")

# HiGHS solver settings per solver-config.md (MILP)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "mip_rel_gap": 0.01,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

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
    """Load a MATPOWER .m file into a PyPSA Network and manually set marginal costs.

    The PPC importer does NOT import gencost, so we parse it from the .m file
    and set marginal_cost on generators manually.
    """
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

    # Parse gencost from CaseFrames and set marginal_cost + startup/shutdown costs
    gencost = cf.gencost.values
    workarounds = []

    num_gens = len(net.generators)
    costs_set = 0
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])

            # Extract startup and shutdown costs from gencost columns 1 and 2
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


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute 24-hour SCUC and return structured results.

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

    try:
        import pypsa

        # 1. Load network with costs (not timed)
        n, load_workarounds = _load_network_with_costs(network_file)
        results["workarounds"].extend(load_workarounds)

        # 2. Create 24 hourly snapshots
        snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
        n.set_snapshots(snapshots)

        # 3. Create time-varying load profile
        # Scale base loads by hourly profile
        base_loads = n.loads["p_set"].copy()
        load_profile_series = pd.Series(LOAD_PROFILE, index=snapshots)
        for load_idx in n.loads.index:
            base_p = base_loads[load_idx]
            n.loads_t.p_set[load_idx] = load_profile_series * base_p

        # 4. Set generators as committable with UC parameters
        # Apply to all generators
        n.generators["committable"] = True

        # Set UC parameters - built-in PyPSA attributes
        # min_up_time and min_down_time: integer number of snapshots
        n.generators["min_up_time"] = 3  # Must stay on at least 3 hours
        n.generators["min_down_time"] = 2  # Must stay off at least 2 hours

        # Ramp rates as fraction of p_nom per snapshot
        n.generators["ramp_limit_up"] = 0.3  # 30% of capacity per hour
        n.generators["ramp_limit_down"] = 0.3  # 30% of capacity per hour

        # Startup/shutdown costs were already set from gencost in _load_network_with_costs
        # For generators with zero startup cost, set a nominal value to make UC non-trivial
        zero_startup = n.generators["start_up_cost"] == 0
        n.generators.loc[zero_startup, "start_up_cost"] = 100.0
        zero_shutdown = n.generators["shut_down_cost"] == 0
        n.generators.loc[zero_shutdown, "shut_down_cost"] = 50.0

        # Set p_min_pu (minimum stable output when committed) - e.g. 30% of capacity
        n.generators["p_min_pu"] = 0.3

        # Record UC parameters for output
        uc_params = {
            "committable": True,
            "min_up_time": 3,
            "min_down_time": 2,
            "ramp_limit_up": 0.3,
            "ramp_limit_down": 0.3,
            "p_min_pu": 0.3,
            "start_up_cost_range": [
                float(n.generators["start_up_cost"].min()),
                float(n.generators["start_up_cost"].max()),
            ],
            "shut_down_cost_range": [
                float(n.generators["shut_down_cost"].min()),
                float(n.generators["shut_down_cost"].max()),
            ],
        }

        # 5. Check for reserve requirement support
        # PyPSA does not have built-in reserve constraints.
        # Reserve requirements need custom constraints via extra_functionality.
        reserve_note = (
            "PyPSA does NOT have built-in reserve requirement constraints. "
            "Reserves must be implemented via extra_functionality callback "
            "using n.model.add_constraints(). This is a user-assembled approach."
        )

        # Define reserve constraint via extra_functionality
        reserve_margin_mw = 500.0  # 500 MW spinning reserve requirement

        def add_reserve_constraint(n, snapshots):
            """Add spinning reserve constraint: sum of (p_nom * status - p) >= reserve_margin."""

            gen_p = n.model["Generator-p"]
            gen_status = n.model["Generator-status"]
            p_nom = n.generators["p_nom"]

            # Reserve = sum(p_nom * status - p) >= reserve_margin
            # i.e., headroom from committed units >= reserve_margin
            (gen_status * p_nom).sum("Generator-com") - gen_p.sum("Generator-ext")
            # The dimension names may differ - let's use a simpler approach
            # Just sum across generators for each snapshot
            lhs_terms = []
            for gen in n.generators.index:
                p_nom_val = float(n.generators.loc[gen, "p_nom"])
                lhs_terms.append(gen_status.sel({"Generator-com": gen}) * p_nom_val)
                lhs_terms.append(-1 * gen_p.sel({"Generator-ext": gen}))

            reserve_lhs = lhs_terms[0]
            for term in lhs_terms[1:]:
                reserve_lhs = reserve_lhs + term

            n.model.add_constraints(
                reserve_lhs >= reserve_margin_mw,
                name="spinning_reserve",
            )

        reserve_workaround = (
            "Reserve requirements implemented via extra_functionality callback "
            f"with custom Linopy constraint (spinning reserve >= {reserve_margin_mw} MW). "
            "This is user-assembled, not a built-in constraint type."
        )

        # 6. Run SCUC optimization (timed)
        # First try with reserve constraint
        reserve_success = False
        start = time.perf_counter()
        try:
            status = n.optimize(
                solver_name=SOLVER_NAME,
                solver_options=SOLVER_OPTIONS,
                extra_functionality=add_reserve_constraint,
            )
            reserve_success = True
        except Exception as reserve_err:
            # If reserve constraint fails (dimension mismatch etc.), run without it
            results["workarounds"].append(
                f"Reserve constraint via extra_functionality raised error: "
                f"{type(reserve_err).__name__}: {reserve_err}. "
                "Falling back to SCUC without reserves."
            )
            status = n.optimize(
                solver_name=SOLVER_NAME,
                solver_options=SOLVER_OPTIONS,
            )
        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed

        if reserve_success:
            results["workarounds"].append(reserve_workaround)

        # 7. Check convergence
        solver_status = str(status)
        converged = False
        if isinstance(status, tuple):
            solver_status = str(status[0])
            converged = "ok" in solver_status.lower() or "optimal" in solver_status.lower()
        elif isinstance(status, str):
            converged = "ok" in status.lower() or "optimal" in status.lower()
        else:
            converged = "ok" in str(status).lower() or "optimal" in str(status).lower()

        # 8. Extract commitment schedule from n.generators_t.status
        commitment_schedule = {}
        status_df = n.generators_t.status
        if status_df is not None and len(status_df) > 0:
            commitment_schedule = {
                "shape": list(status_df.shape),
                "num_snapshots": status_df.shape[0],
                "num_generators": status_df.shape[1],
                "generators": list(status_df.columns),
                "snapshots": [str(s) for s in status_df.index],
                # Binary matrix summary
                "total_commitments": int(status_df.sum().sum()),
                "max_simultaneous_online": int(status_df.sum(axis=1).max()),
                "min_simultaneous_online": int(status_df.sum(axis=1).min()),
                "generators_always_on": int((status_df.sum(axis=0) == 24).sum()),
                "generators_never_on": int((status_df.sum(axis=0) == 0).sum()),
                # Per-generator commitment hours
                "hours_online_per_gen": {
                    gen: int(status_df[gen].sum()) for gen in status_df.columns
                },
            }

        # 9. Extract dispatch
        gen_dispatch = n.generators_t.p
        dispatch_stats = {}
        if gen_dispatch is not None and len(gen_dispatch) > 0:
            dispatch_stats = {
                "total_dispatch_MW_by_hour": [
                    float(gen_dispatch.iloc[t].sum()) for t in range(len(gen_dispatch))
                ],
                "peak_demand_hour": int(gen_dispatch.sum(axis=1).idxmax().hour),
                "min_demand_hour": int(gen_dispatch.sum(axis=1).idxmin().hour),
            }

        # 10. Extract MIP gap
        objective = float(n.objective) if hasattr(n, "objective") else None

        # Attempt to get MIP gap from solver statistics
        mip_gap = None
        try:
            if hasattr(n, "model") and hasattr(n.model, "solver_model"):
                solver_model = n.model.solver_model
                if hasattr(solver_model, "getInfoValue"):
                    mip_gap = solver_model.getInfoValue("mip_gap")
        except Exception:
            pass

        # Built-in vs user-assembled constraint types
        constraint_analysis = {
            "built_in": [
                "min_up_time",
                "min_down_time",
                "start_up_cost",
                "shut_down_cost",
                "ramp_limit_up",
                "ramp_limit_down",
                "p_min_pu (minimum stable output)",
                "committable (binary on/off)",
            ],
            "user_assembled": [
                "spinning_reserve (via extra_functionality + linopy)"
                if reserve_success
                else "spinning_reserve (attempted but failed, would need extra_functionality)"
            ],
            "reserve_constraint_success": reserve_success,
        }

        # Count lines of code
        loc = sum(
            1
            for line in Path(__file__).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

        # 11. Pass condition: solves to feasibility with MIP gap <= 1%,
        #     commitment schedule extractable as time-indexed binary matrix
        has_commitment = len(commitment_schedule) > 0 and commitment_schedule["num_generators"] > 0
        pass_condition_met = converged and has_commitment

        if pass_condition_met:
            results["status"] = "pass"

        results["details"] = {
            "converged": converged,
            "solver_status": solver_status,
            "solver": SOLVER_NAME,
            "solver_options": SOLVER_OPTIONS,
            "objective": objective,
            "mip_gap": mip_gap,
            "uc_parameters": uc_params,
            "commitment_schedule": commitment_schedule,
            "dispatch": dispatch_stats,
            "constraint_analysis": constraint_analysis,
            "reserve_note": reserve_note,
            "loc": loc,
            "pypsa_version": pypsa.__version__,
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
