"""A-6 (sced) -- Fix commitment from A-5, solve economic dispatch on IEEE 39-bus (TINY).

depends_on: A-5 (SCUC passed on TINY)
Pass condition: UC and ED cleanly separable as two-stage workflow. Ramp rate
constraints demonstrably enforced in ED stage.
Solver: HiGHS
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case39.m")


def load_network_with_costs(filepath: str | Path) -> pypsa.Network:
    """Load network with linear costs (HiGHS cannot solve MIQP)."""
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    if hasattr(cf, "gencost") and cf.gencost is not None:
        ppc["gencost"] = cf.gencost.values
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)

    # Linear costs differentiated across generators (same as A-5)
    gencost = cf.gencost
    cost_offsets = [0.0, 0.5, 1.0, 1.5, 2.0, 0.8, 1.2, 1.8, 0.3, 0.6]
    for i, gen_name in enumerate(n.generators.index):
        row = gencost.iloc[i]
        base_mc = row["C1"]
        n.generators.loc[gen_name, "marginal_cost"] = base_mc + cost_offsets[i]
    return n


def setup_uc_network(n: pypsa.Network) -> pypsa.Network:
    """Configure 24-hour snapshots, load profile, and UC parameters."""
    snapshots = pd.date_range("2024-01-01", periods=24, freq="h")
    n.set_snapshots(snapshots)

    # Time-varying load profile (same as A-5)
    base_loads = n.loads.p_set.copy()
    load_profile = np.array(
        [
            0.65,
            0.60,
            0.58,
            0.56,
            0.58,
            0.65,
            0.78,
            0.90,
            0.95,
            0.98,
            1.00,
            0.99,
            0.97,
            0.96,
            0.95,
            0.96,
            0.98,
            1.00,
            0.99,
            0.95,
            0.90,
            0.82,
            0.75,
            0.68,
        ]
    )
    for load_name in n.loads.index:
        n.loads_t.p_set[load_name] = base_loads[load_name] * load_profile

    # UC parameters
    for gen_name in n.generators.index:
        n.generators.loc[gen_name, "committable"] = True
        n.generators.loc[gen_name, "min_up_time"] = 3
        n.generators.loc[gen_name, "min_down_time"] = 2
        n.generators.loc[gen_name, "start_up_cost"] = 500.0
        n.generators.loc[gen_name, "shut_down_cost"] = 200.0
        n.generators.loc[gen_name, "ramp_limit_up"] = 0.3
        n.generators.loc[gen_name, "ramp_limit_down"] = 0.3
        n.generators.loc[gen_name, "p_min_pu"] = 0.2

    return n


def run() -> dict:
    """Execute A-6 SCED two-stage test."""
    errors = []
    workarounds = []
    details = {}

    try:
        # ===== STAGE 1: SCUC (unit commitment) =====
        n = load_network_with_costs(CASE_FILE)
        n = setup_uc_network(n)

        t0 = time.perf_counter()
        uc_status = n.optimize(
            solver_name="highs",
            solver_options={
                "time_limit": 300,
                "presolve": "on",
                "threads": 1,
                "mip_rel_gap": 0.01,
            },
        )
        uc_time = time.perf_counter() - t0

        details["stage1_uc_solver_status"] = str(uc_status)
        details["stage1_uc_objective"] = round(float(n.objective), 2)
        details["stage1_uc_wall_clock_seconds"] = round(uc_time, 6)

        # Extract commitment schedule
        commitment = n.generators_t.status.copy()
        details["commitment_shape"] = list(commitment.shape)
        details["commitment_sample"] = {
            gen: [int(v) for v in commitment[gen].values[:6]] for gen in commitment.columns[:4]
        }

        # ===== STAGE 2: Fix commitment, solve ED as LP =====
        # Key approach: set committable=False, use p_min_pu from commitment status
        # When status=0, generator is OFF -> p_min_pu=0, p_max_pu=0
        # When status=1, generator is ON  -> p_min_pu=0.2, p_max_pu=1.0

        workarounds.append(
            {
                "type": "stable",
                "description": (
                    "Two-stage UC/ED separation requires manual commitment fixation: "
                    "set committable=False, then use p_min_pu (time-varying) = status * min_stable_level "
                    "and p_max_pu (time-varying) = status to enforce the commitment schedule."
                ),
            }
        )

        # Store original ramp limits before disabling committable
        ramp_limits = {}
        for gen_name in n.generators.index:
            ramp_limits[gen_name] = {
                "ramp_limit_up": n.generators.loc[gen_name, "ramp_limit_up"],
                "ramp_limit_down": n.generators.loc[gen_name, "ramp_limit_down"],
            }

        # Fix commitment by making generators non-committable and setting time-varying bounds
        for gen_name in n.generators.index:
            n.generators.loc[gen_name, "committable"] = False
            # Time-varying p_min_pu and p_max_pu based on commitment status
            status_series = commitment[gen_name]
            # When committed (status=1): p_min_pu=0.2 (minimum stable), p_max_pu=1.0
            # When not committed (status=0): p_min_pu=0, p_max_pu=0
            n.generators_t.p_min_pu[gen_name] = status_series * 0.2
            n.generators_t.p_max_pu[gen_name] = status_series * 1.0

        details["stage2_commitment_fixed"] = True
        details["stage2_method"] = (
            "committable=False, p_min_pu=status*0.2, p_max_pu=status*1.0 (time-varying)"
        )

        # Ramp limits are still on generators from stage 1 -- they apply to the LP too
        details["ramp_limits_preserved"] = True

        # Solve ED (now LP since committable=False)
        t0 = time.perf_counter()
        ed_status = n.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        ed_time = time.perf_counter() - t0

        details["stage2_ed_solver_status"] = str(ed_status)
        details["stage2_ed_objective"] = round(float(n.objective), 2)
        details["stage2_ed_wall_clock_seconds"] = round(ed_time, 6)

        # Extract ED dispatch
        ed_dispatch = n.generators_t.p
        details["ed_dispatch_shape"] = list(ed_dispatch.shape)
        details["ed_total_dispatch_by_hour"] = [
            round(float(v), 1) for v in ed_dispatch.sum(axis=1).values
        ]

        # ===== Verify ramp constraints enforced =====
        ramp_violations = []
        ramp_checks = {}
        for gen_name in n.generators.index:
            p_series = ed_dispatch[gen_name].values
            p_nom = n.generators.loc[gen_name, "p_nom"]
            ramp_up_limit = ramp_limits[gen_name]["ramp_limit_up"] * p_nom
            ramp_down_limit = ramp_limits[gen_name]["ramp_limit_down"] * p_nom

            # Check consecutive-period dispatch changes
            deltas = np.diff(p_series)
            max_ramp_up = float(np.max(deltas)) if len(deltas) > 0 else 0.0
            max_ramp_down = float(np.min(deltas)) if len(deltas) > 0 else 0.0

            ramp_checks[gen_name] = {
                "p_nom": round(p_nom, 1),
                "ramp_up_limit_mw": round(ramp_up_limit, 1),
                "ramp_down_limit_mw": round(ramp_down_limit, 1),
                "max_ramp_up_mw": round(max_ramp_up, 1),
                "max_ramp_down_mw": round(max_ramp_down, 1),
                "ramp_up_ok": max_ramp_up <= ramp_up_limit + 0.1,  # small tolerance
                "ramp_down_ok": abs(max_ramp_down) <= ramp_down_limit + 0.1,
            }

            # Note: when a unit starts up (status 0->1), the ramp from 0 to p_min
            # is not a ramp violation per se, but we check dispatch-to-dispatch ramps
            # only for periods where unit is ON in both consecutive hours.
            status_vals = commitment[gen_name].values
            for t_idx in range(len(deltas)):
                # Only check ramp when unit is ON in both periods
                if status_vals[t_idx] >= 0.5 and status_vals[t_idx + 1] >= 0.5:
                    delta = deltas[t_idx]
                    if delta > ramp_up_limit + 0.1:
                        ramp_violations.append(
                            {
                                "gen": gen_name,
                                "hour": t_idx,
                                "delta_mw": round(delta, 2),
                                "limit_mw": round(ramp_up_limit, 2),
                                "direction": "up",
                            }
                        )
                    if delta < -(ramp_down_limit + 0.1):
                        ramp_violations.append(
                            {
                                "gen": gen_name,
                                "hour": t_idx,
                                "delta_mw": round(delta, 2),
                                "limit_mw": round(-ramp_down_limit, 2),
                                "direction": "down",
                            }
                        )

        details["ramp_checks"] = ramp_checks
        details["ramp_violations"] = ramp_violations
        details["ramp_constraints_enforced"] = len(ramp_violations) == 0

        # Verify decommitted generators have zero dispatch
        zero_dispatch_check = {}
        for gen_name in n.generators.index:
            status_vals = commitment[gen_name].values
            dispatch_vals = ed_dispatch[gen_name].values
            off_hours = np.where(status_vals < 0.5)[0]
            if len(off_hours) > 0:
                max_dispatch_when_off = float(np.max(np.abs(dispatch_vals[off_hours])))
                zero_dispatch_check[gen_name] = {
                    "off_hours": len(off_hours),
                    "max_dispatch_when_off": round(max_dispatch_when_off, 4),
                    "correctly_zero": max_dispatch_when_off < 0.01,
                }
        details["zero_dispatch_when_off"] = zero_dispatch_check

        # Two-stage workflow summary
        details["two_stage_workflow"] = {
            "stage1": "SCUC (MILP with committable=True)",
            "stage2": "ED (LP with committable=False, commitment fixed via p_min_pu/p_max_pu)",
            "separation_method": "manual (set time-varying bounds from commitment schedule)",
            "cleanly_separable": True,
        }

        assert len(ramp_violations) == 0, f"Ramp violations found: {ramp_violations}"
        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")

    return {
        "test_id": "A-6",
        "slug": "sced",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": (
            details.get("stage1_uc_wall_clock_seconds", 0.0)
            + details.get("stage2_ed_wall_clock_seconds", 0.0)
        ),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
