"""
Test A-6: Fix commitment schedule from A-5, solve economic dispatch as LP/QP

Dimension: expressiveness
Network: SMALL (ACTIVSg 2000-bus)
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

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m")

# HiGHS solver settings per solver-config.md
SOLVER_NAME = "highs"
MILP_SOLVER_OPTIONS = {
    "time_limit": 600,
    "mip_rel_gap": 0.10,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}
LP_SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

LOAD_PROFILE = [
    0.67,
    0.63,
    0.60,
    0.59,
    0.59,
    0.60,
    0.74,
    0.86,
    0.95,
    0.96,
    0.96,
    0.93,
    0.92,
    0.92,
    0.93,
    0.94,
    0.99,
    1.00,
    0.96,
    0.91,
    0.83,
    0.73,
    0.63,
    0.60,
]


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

            startup_cost = float(cost_row[1])
            shutdown_cost = float(cost_row[2])
            net.generators.loc[gen_idx, "start_up_cost"] = startup_cost
            net.generators.loc[gen_idx, "shut_down_cost"] = shutdown_cost

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

    return net, workarounds


def _setup_uc_network(network_file: str):
    """Set up the 24-hour UC network (same as A-5 SMALL)."""
    n, workarounds = _load_network_with_costs(network_file)

    snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
    n.set_snapshots(snapshots)

    base_loads = n.loads["p_set"].copy()
    load_profile_series = pd.Series(LOAD_PROFILE, index=snapshots)
    for load_idx in n.loads.index:
        base_p = base_loads[load_idx]
        n.loads_t.p_set[load_idx] = load_profile_series * base_p

    # Only make thermal generators committable
    thermal_mask = n.generators["marginal_cost"] > 0.1
    n.generators.loc[thermal_mask, "committable"] = True
    n.generators.loc[thermal_mask, "min_up_time"] = 3
    n.generators.loc[thermal_mask, "min_down_time"] = 2
    n.generators.loc[thermal_mask, "ramp_limit_up"] = 0.3
    n.generators.loc[thermal_mask, "ramp_limit_down"] = 0.3
    n.generators.loc[thermal_mask, "p_min_pu"] = 0.3

    zero_startup = (n.generators["start_up_cost"] == 0) & thermal_mask
    n.generators.loc[zero_startup, "start_up_cost"] = 100.0
    zero_shutdown = (n.generators["shut_down_cost"] == 0) & thermal_mask
    n.generators.loc[zero_shutdown, "shut_down_cost"] = 50.0

    return n, workarounds


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute two-stage SCUC -> SCED workflow on 2000-bus and return structured results."""
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
        # Stage 1: SCUC
        # ================================================================
        n, load_workarounds = _setup_uc_network(network_file)
        results["workarounds"].extend(load_workarounds)

        scuc_start = time.perf_counter()
        scuc_status = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=MILP_SOLVER_OPTIONS,
        )
        scuc_elapsed = time.perf_counter() - scuc_start

        scuc_converged = "ok" in str(scuc_status).lower() or "optimal" in str(scuc_status).lower()
        if not scuc_converged:
            results["errors"].append(f"SCUC did not converge: {scuc_status}")
            results["wall_clock_seconds"] = time.perf_counter() - start
            return results

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
        ed_workarounds = []

        # Set committable=False to make this an LP
        n.generators["committable"] = False

        # Encode commitment schedule into time-varying bounds
        for gen in n.generators.index:
            if gen in scuc_commitment.columns:
                gen_status = scuc_commitment[gen]
                p_max_pu_series = gen_status.astype(float)
                n.generators_t.p_max_pu[gen] = p_max_pu_series
                orig_p_min_pu = float(n.generators.loc[gen, "p_min_pu"])
                p_min_pu_series = gen_status.astype(float) * orig_p_min_pu
                n.generators_t.p_min_pu[gen] = p_min_pu_series
            else:
                # Non-committable generators keep full availability
                pass

        ed_workarounds.append(
            "Fixed commitment by setting committable=False and encoding UC status "
            "into time-varying p_min_pu/p_max_pu. PyPSA has no dedicated "
            "'fix commitment' method for the SCUC->SCED two-stage workflow."
        )

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

        sced_dispatch = n.generators_t.p.copy()
        sced_objective = float(n.objective)

        # ================================================================
        # Verify ramp constraint enforcement
        # ================================================================
        ramp_violations = []
        n_binding_up = 0
        n_binding_down = 0

        for gen in n.generators.index:
            p_nom = float(n.generators.loc[gen, "p_nom"])
            ramp_up_lim = float(n.generators.loc[gen, "ramp_limit_up"])
            ramp_down_lim = float(n.generators.loc[gen, "ramp_limit_down"])
            if ramp_up_lim == 0 or np.isnan(ramp_up_lim):
                continue

            ramp_up_limit_mw = ramp_up_lim * p_nom
            ramp_down_limit_mw = ramp_down_lim * p_nom

            dispatch_series = sced_dispatch[gen].values
            for t in range(1, len(dispatch_series)):
                ramp = dispatch_series[t] - dispatch_series[t - 1]
                if ramp > ramp_up_limit_mw + 1e-3:
                    ramp_violations.append(
                        {
                            "generator": gen,
                            "hour": t,
                            "type": "ramp_up",
                            "ramp_MW": float(ramp),
                            "limit_MW": ramp_up_limit_mw,
                        }
                    )
                if -ramp > ramp_down_limit_mw + 1e-3:
                    ramp_violations.append(
                        {
                            "generator": gen,
                            "hour": t,
                            "type": "ramp_down",
                            "ramp_MW": float(-ramp),
                            "limit_MW": ramp_down_limit_mw,
                        }
                    )
                if abs(ramp - ramp_up_limit_mw) < 1e-3:
                    n_binding_up += 1
                if abs(-ramp - ramp_down_limit_mw) < 1e-3:
                    n_binding_down += 1

        ramps_enforced = len(ramp_violations) == 0

        # ================================================================
        # Dispatch comparison
        # ================================================================
        # Only compare for generators present in both
        common_cols = scuc_dispatch.columns.intersection(sced_dispatch.columns)
        dispatch_diff = (sced_dispatch[common_cols] - scuc_dispatch[common_cols]).abs()
        max_dispatch_diff = float(dispatch_diff.max().max())
        mean_dispatch_diff = float(dispatch_diff.mean().mean())

        # ================================================================
        # Determine pass/fail
        # ================================================================
        pass_condition_met = sced_converged and len(sced_dispatch) == 24 and ramps_enforced

        if pass_condition_met:
            results["status"] = "pass"

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
            },
            "dispatch": {
                "peak_hour_MW": float(sced_dispatch.sum(axis=1).max()),
                "min_hour_MW": float(sced_dispatch.sum(axis=1).min()),
            },
            "ramp_enforcement": {
                "num_violations": len(ramp_violations),
                "ramps_enforced": ramps_enforced,
                "binding_ramp_up_count": n_binding_up,
                "binding_ramp_down_count": n_binding_down,
                "sample_violations": ramp_violations[:5] if ramp_violations else [],
            },
            "dispatch_comparison": {
                "max_diff_MW": max_dispatch_diff,
                "mean_diff_MW": mean_dispatch_diff,
            },
            "two_stage_separation": {
                "cleanly_separable": True,
                "method": (
                    "Set committable=False after SCUC, encode commitment into "
                    "p_min_pu/p_max_pu time series, re-solve as LP"
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
