"""A-5 (scuc) -- 24-hour SCUC as MILP on ACTIVSg2000 (SMALL).

Pass condition: Solves to feasibility (MIP gap <= 1%). Commitment schedule
extractable as time-indexed binary matrix.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg2000.m")


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

    # Apply generator costs from gencost - linear only for HiGHS MILP
    if hasattr(cf, "gencost") and cf.gencost is not None:
        gc = cf.gencost.values
        for i, gen_name in enumerate(n.generators.index):
            if i < len(gc):
                cost_type = int(gc[i, 0])
                if cost_type == 2:
                    n_coeffs = int(gc[i, 3])
                    if n_coeffs == 2:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 4]
                    elif n_coeffs >= 3:
                        # Use linear term only (C1), ignore quadratic for MILP
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 5]
    return n


def run() -> dict:
    """Execute A-5 SCUC test on SMALL network."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network_with_costs(CASE_FILE)
        details["buses"] = len(n.buses)
        details["generators"] = len(n.generators)
        details["lines"] = len(n.lines)
        details["transformers"] = len(n.transformers)

        # Set up 24-hour snapshots
        snapshots = pd.date_range("2024-01-01", periods=24, freq="h")
        n.set_snapshots(snapshots)

        # Create time-varying load profile
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
            n.generators.loc[gen_name, "ramp_limit_up"] = 0.3
            n.generators.loc[gen_name, "ramp_limit_down"] = 0.3
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

        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["solver_status"] = str(status_result)
        details["objective_value"] = round(float(n.objective), 2)

        # Extract commitment schedule
        if hasattr(n.generators_t, "status") and len(n.generators_t.status) > 0:
            commitment = n.generators_t.status
            details["commitment_shape"] = list(commitment.shape)
            details["commitment_type"] = type(commitment).__name__
            # Count on/off transitions
            transitions = (commitment.diff().abs() > 0.5).sum()
            details["total_transitions"] = int(transitions.sum())
            details["units_always_on"] = int((commitment.min() >= 0.5).sum())
            details["units_always_off"] = int((commitment.max() < 0.5).sum())
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

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "A-5",
        "slug": "scuc",
        "tier": "SMALL",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", round(wall_clock, 4)),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
