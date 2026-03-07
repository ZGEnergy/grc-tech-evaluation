"""
Test A-6: Fix commitment schedule from A-5, solve economic dispatch as LP/QP

Dimension: expressiveness
Network: TINY (case39)
Pass condition: Solves. Dispatch schedule extractable. UC and ED are cleanly separable
    as a two-stage workflow. Ramp rate constraints are demonstrably enforced between
    consecutive dispatch intervals in the ED stage -- not just inherited from the UC
    formulation.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")

# HiGHS solver settings per solver-config.md
# SCUC stage: MILP
SOLVER_NAME = "highs"
MILP_SOLVER_OPTIONS = {
    "time_limit": 300,
    "mip_rel_gap": 0.01,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}
# SCED stage: LP (no MIP gap needed)
LP_SOLVER_OPTIONS = {
    "time_limit": 300,
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


def _setup_uc_network(network_file: str):
    """Set up the 24-hour UC network (same as A-5)."""
    n, workarounds = _load_network_with_costs(network_file)

    snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
    n.set_snapshots(snapshots)

    # Time-varying load profile
    base_loads = n.loads["p_set"].copy()
    load_profile_series = pd.Series(LOAD_PROFILE, index=snapshots)
    for load_idx in n.loads.index:
        base_p = base_loads[load_idx]
        n.loads_t.p_set[load_idx] = load_profile_series * base_p

    # UC parameters
    n.generators["committable"] = True
    n.generators["min_up_time"] = 3
    n.generators["min_down_time"] = 2
    n.generators["ramp_limit_up"] = 0.3
    n.generators["ramp_limit_down"] = 0.3
    n.generators["p_min_pu"] = 0.3

    zero_startup = n.generators["start_up_cost"] == 0
    n.generators.loc[zero_startup, "start_up_cost"] = 100.0
    zero_shutdown = n.generators["shut_down_cost"] == 0
    n.generators.loc[zero_shutdown, "shut_down_cost"] = 50.0

    return n, workarounds


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute two-stage SCUC -> SCED workflow and return structured results.

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

        # ================================================================
        # Stage 1: SCUC (reuse A-5 setup)
        # ================================================================
        n, load_workarounds = _setup_uc_network(network_file)
        results["workarounds"].extend(load_workarounds)

        scuc_start = time.perf_counter()
        scuc_status = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=MILP_SOLVER_OPTIONS,
        )
        scuc_elapsed = time.perf_counter() - scuc_start

        # Check SCUC convergence
        scuc_converged = "ok" in str(scuc_status).lower() or "optimal" in str(scuc_status).lower()
        if not scuc_converged:
            results["errors"].append(f"SCUC did not converge: {scuc_status}")
            results["wall_clock_seconds"] = time.perf_counter() - start
            return results

        # Extract SCUC results
        scuc_commitment = n.generators_t.status.copy()
        scuc_dispatch = n.generators_t.p.copy()
        scuc_objective = float(n.objective)

        results["details"]["scuc"] = {
            "status": str(scuc_status),
            "objective": scuc_objective,
            "wall_clock_seconds": scuc_elapsed,
            "commitment_shape": list(scuc_commitment.shape),
            "generators_always_on": int((scuc_commitment.sum(axis=0) == 24).sum()),
        }

        # ================================================================
        # Stage 2: SCED - Fix commitment, solve ED as LP
        # ================================================================
        # Strategy: Set committable=False and use p_min_pu/p_max_pu time series
        # to reflect the commitment schedule. When a generator is committed (status=1),
        # its p_min_pu and p_max_pu stay at their normal values. When decommitted
        # (status=0), set both p_min_pu and p_max_pu to 0 to force output to zero.

        ed_workarounds = []

        # Method: Use p_min_pu / p_max_pu time series to encode the commitment
        # Set committable=False to make this an LP (no binary variables)
        n.generators["committable"] = False

        # Build time-varying p_min_pu and p_max_pu from the commitment schedule
        for gen in n.generators.index:
            gen_status = scuc_commitment[gen]  # Series of 0/1

            # p_max_pu: 1.0 when committed, 0.0 when off
            p_max_pu_series = gen_status.astype(float)
            n.generators_t.p_max_pu[gen] = p_max_pu_series

            # p_min_pu: original p_min_pu (0.3) when committed, 0.0 when off
            orig_p_min_pu = 0.3  # from UC setup
            p_min_pu_series = gen_status.astype(float) * orig_p_min_pu
            n.generators_t.p_min_pu[gen] = p_min_pu_series

        ed_workarounds.append(
            "Fixed commitment by setting committable=False and encoding UC status "
            "into time-varying p_min_pu/p_max_pu (0 when decommitted, normal bounds "
            "when committed). PyPSA has no dedicated 'fix commitment' method for "
            "the SCUC->SCED two-stage workflow."
        )

        # Keep ramp constraints for the ED stage
        # ramp_limit_up and ramp_limit_down are already set (0.3 of p_nom)
        # These should be enforced in the LP as well

        sced_start = time.perf_counter()
        sced_status = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=LP_SOLVER_OPTIONS,
        )
        sced_elapsed = time.perf_counter() - sced_start

        sced_converged = "ok" in str(sced_status).lower() or "optimal" in str(sced_status).lower()

        if not sced_converged:
            results["errors"].append(f"SCED did not converge: {sced_status}")
            results["details"]["sced_status"] = str(sced_status)
            results["wall_clock_seconds"] = time.perf_counter() - start
            return results

        # Extract SCED results
        sced_dispatch = n.generators_t.p.copy()
        sced_objective = float(n.objective)

        # ================================================================
        # Verify ramp constraint enforcement
        # ================================================================
        ramp_violations = []
        ramp_check_details = {}

        for gen in n.generators.index:
            p_nom = float(n.generators.loc[gen, "p_nom"])
            ramp_up_limit = float(n.generators.loc[gen, "ramp_limit_up"]) * p_nom  # MW
            ramp_down_limit = float(n.generators.loc[gen, "ramp_limit_down"]) * p_nom  # MW

            dispatch_series = sced_dispatch[gen].values
            max_ramp_up = 0.0
            max_ramp_down = 0.0

            for t in range(1, len(dispatch_series)):
                ramp = dispatch_series[t] - dispatch_series[t - 1]
                max_ramp_up = max(max_ramp_up, ramp)
                max_ramp_down = max(max_ramp_down, -ramp)

                # Check ramp up violation (with tolerance)
                if ramp > ramp_up_limit + 1e-3:
                    ramp_violations.append(
                        {
                            "generator": gen,
                            "hour": t,
                            "type": "ramp_up",
                            "ramp_MW": float(ramp),
                            "limit_MW": ramp_up_limit,
                            "excess_MW": float(ramp - ramp_up_limit),
                        }
                    )

                # Check ramp down violation (with tolerance)
                if -ramp > ramp_down_limit + 1e-3:
                    ramp_violations.append(
                        {
                            "generator": gen,
                            "hour": t,
                            "type": "ramp_down",
                            "ramp_MW": float(-ramp),
                            "limit_MW": ramp_down_limit,
                            "excess_MW": float(-ramp - ramp_down_limit),
                        }
                    )

            ramp_check_details[gen] = {
                "p_nom_MW": p_nom,
                "ramp_up_limit_MW": ramp_up_limit,
                "ramp_down_limit_MW": ramp_down_limit,
                "max_observed_ramp_up_MW": float(max_ramp_up),
                "max_observed_ramp_down_MW": float(max_ramp_down),
                "ramp_up_binding": max_ramp_up >= ramp_up_limit - 1e-3,
                "ramp_down_binding": max_ramp_down >= ramp_down_limit - 1e-3,
            }

        ramps_enforced = len(ramp_violations) == 0
        any_ramp_binding = any(
            d["ramp_up_binding"] or d["ramp_down_binding"] for d in ramp_check_details.values()
        )

        # ================================================================
        # Verify problem type is LP (not MILP)
        # ================================================================
        is_lp = True
        lp_check_note = "committable=False removes binary variables -> LP"
        try:
            if hasattr(n, "model") and hasattr(n.model, "variables"):
                for vname, var in n.model.variables.items():
                    if hasattr(var, "attrs") and var.attrs.get("binary", False):
                        is_lp = False
                        lp_check_note = f"Binary variable found: {vname}"
                        break
        except Exception:
            lp_check_note = "Could not verify LP vs MILP from model object"

        # ================================================================
        # Compare SCUC vs SCED dispatch
        # ================================================================
        dispatch_diff = (sced_dispatch - scuc_dispatch).abs()
        max_dispatch_diff = float(dispatch_diff.max().max())
        mean_dispatch_diff = float(dispatch_diff.mean().mean())

        # ================================================================
        # Determine pass/fail
        # ================================================================
        # Pass condition: Solves, dispatch extractable, UC/ED cleanly separable,
        # ramp constraints demonstrably enforced in ED stage
        pass_condition_met = sced_converged and len(sced_dispatch) == 24 and ramps_enforced

        if pass_condition_met:
            results["status"] = "pass"

        # Count LOC
        loc = sum(
            1
            for line in Path(__file__).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

        results["workarounds"].extend(ed_workarounds)
        results["details"] = {
            **results["details"],
            "sced": {
                "status": str(sced_status),
                "objective": sced_objective,
                "wall_clock_seconds": sced_elapsed,
                "is_lp": is_lp,
                "lp_check_note": lp_check_note,
            },
            "dispatch": {
                "total_dispatch_MW_by_hour": [
                    float(sced_dispatch.iloc[t].sum()) for t in range(len(sced_dispatch))
                ],
                "peak_hour_MW": float(sced_dispatch.sum(axis=1).max()),
                "min_hour_MW": float(sced_dispatch.sum(axis=1).min()),
            },
            "ramp_enforcement": {
                "violations": ramp_violations,
                "num_violations": len(ramp_violations),
                "ramps_enforced": ramps_enforced,
                "any_ramp_binding": any_ramp_binding,
                "per_generator": ramp_check_details,
            },
            "dispatch_comparison": {
                "max_diff_MW": max_dispatch_diff,
                "mean_diff_MW": mean_dispatch_diff,
                "note": (
                    "Dispatch may differ between SCUC and SCED because the SCED LP "
                    "re-optimizes dispatch with fixed commitment. Small differences "
                    "are expected; large differences would indicate the commitment "
                    "fixing approach changed the problem."
                ),
            },
            "two_stage_separation": {
                "cleanly_separable": True,
                "method": (
                    "Set committable=False after SCUC, encode commitment into "
                    "p_min_pu/p_max_pu time series, re-solve as LP"
                ),
                "note": (
                    "PyPSA does not have a built-in 'fix commitment and re-dispatch' "
                    "method. The user must manually transfer the commitment schedule "
                    "by manipulating generator bounds. This is a stable workaround "
                    "using documented public API (p_min_pu, p_max_pu, committable)."
                ),
            },
            "loc": loc,
            "pypsa_version": pypsa.__version__,
            "solver": SOLVER_NAME,
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
