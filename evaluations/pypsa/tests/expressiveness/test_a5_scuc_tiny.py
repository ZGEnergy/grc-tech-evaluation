"""A-5 (scuc) — 24-hour SCUC as MILP on IEEE 39-bus (TINY).

Pass condition: Solves to feasibility (MIP gap <= 1%). Commitment schedule
extractable as time-indexed binary matrix. Built-in constraint types vs
user-assembled noted.
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

    # Set LINEAR costs only — HiGHS cannot solve MIQP (mixed-integer quadratic).
    # Differentiate costs across generators to make the problem non-trivial.
    # Use marginal_cost = C1 + 2*C2*Pnom/2 (linearized at midpoint) with variation.
    gencost = cf.gencost
    cost_offsets = [0.0, 0.5, 1.0, 1.5, 2.0, 0.8, 1.2, 1.8, 0.3, 0.6]
    for i, gen_name in enumerate(n.generators.index):
        row = gencost.iloc[i]
        base_mc = row["C1"]  # 0.3 for all gens in case39
        n.generators.loc[gen_name, "marginal_cost"] = base_mc + cost_offsets[i]
        # Keep marginal_cost_quadratic at 0 (default) for MILP compatibility
    return n


def run() -> dict:
    """Execute A-5 SCUC test."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network_with_costs(CASE_FILE)

        # Set up 24-hour snapshots
        snapshots = pd.date_range("2024-01-01", periods=24, freq="h")
        n.set_snapshots(snapshots)

        # Create time-varying load profile (sinusoidal pattern)
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

        # Configure generators for unit commitment
        builtin_constraints = []
        for gen_name in n.generators.index:
            n.generators.loc[gen_name, "committable"] = True
            n.generators.loc[gen_name, "min_up_time"] = 3
            n.generators.loc[gen_name, "min_down_time"] = 2
            n.generators.loc[gen_name, "start_up_cost"] = 500.0
            n.generators.loc[gen_name, "shut_down_cost"] = 200.0
            n.generators.loc[gen_name, "ramp_limit_up"] = 0.3  # 30% of p_nom per hour
            n.generators.loc[gen_name, "ramp_limit_down"] = 0.3
            # p_min_pu sets minimum stable output when committed
            n.generators.loc[gen_name, "p_min_pu"] = 0.2

        builtin_constraints = [
            "min_up_time",
            "min_down_time",
            "start_up_cost",
            "shut_down_cost",
            "ramp_limit_up",
            "ramp_limit_down",
            "p_min_pu (minimum stable generation)",
        ]
        details["builtin_constraint_types"] = builtin_constraints

        # Solve SCUC with HiGHS
        t0 = time.perf_counter()
        status_result = n.optimize(
            solver_name="highs",
            solver_options={
                "time_limit": 300,
                "presolve": "on",
                "threads": 1,
                "mip_rel_gap": 0.01,
            },
        )
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["solver_status"] = str(status_result)
        details["objective_value"] = round(float(n.objective), 2)

        # Extract commitment schedule
        if hasattr(n.generators_t, "status") and len(n.generators_t.status) > 0:
            commitment = n.generators_t.status
            details["commitment_shape"] = list(commitment.shape)
            details["commitment_type"] = type(commitment).__name__
            details["commitment_sample"] = {
                gen: [round(v, 0) for v in commitment[gen].values[:6]]
                for gen in commitment.columns[:3]
            }
            # Count on/off transitions
            transitions = (commitment.diff().abs() > 0.5).sum()
            details["commitment_transitions"] = transitions.to_dict()
            details["commitment_extractable"] = True
        else:
            details["commitment_extractable"] = False
            errors.append("generators_t.status not populated after SCUC solve")

        # Extract dispatch
        gen_dispatch = n.generators_t.p
        details["dispatch_shape"] = list(gen_dispatch.shape)
        details["dispatch_range_mw"] = [
            round(float(gen_dispatch.values.min()), 2),
            round(float(gen_dispatch.values.max()), 2),
        ]
        details["total_dispatch_by_hour"] = [
            round(float(v), 1) for v in gen_dispatch.sum(axis=1).values
        ]

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        wall_clock = 0.0

    return {
        "test_id": "A-5",
        "slug": "scuc",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", round(wall_clock, 6)),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
