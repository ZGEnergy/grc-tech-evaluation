"""
Test A-5: 24-hour SCUC (Security-Constrained Unit Commitment) as MILP

Dimension: expressiveness
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Solves to feasibility (MIP gap <= 1%). Commitment schedule
    extractable as a time-indexed binary matrix. Built-in constraint types
    vs. user-assembled noted.
Tool: pypsa 1.1.2
Solver: HiGHS (MILP)

PyPSA supports unit commitment natively via committable=True on generators.
Built-in parameters: min_up_time, min_down_time, start_up_cost, shut_down_cost,
ramp_limit_up, ramp_limit_down. Reserve requirements require extra_functionality
callback (user-assembled).

Note: PyPSA's pypower importer does NOT import gencost — manual cost assignment required.
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"

# HiGHS solver settings (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300.0,
    "mip_rel_gap": 0.01,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

# 24-hour load profile multipliers (fraction of base load, hourly)
LOAD_PROFILE = np.array(
    [
        0.67,
        0.63,
        0.60,
        0.59,
        0.59,
        0.60,  # HE01-HE06 (overnight)
        0.74,
        0.86,
        0.95,
        0.96,
        0.96,
        0.93,  # HE07-HE12 (morning ramp)
        0.92,
        0.93,
        0.87,
        0.90,
        0.91,
        0.99,  # HE13-HE18 (afternoon)
        1.00,
        0.96,
        0.91,
        0.83,
        0.73,
        0.63,  # HE19-HE24 (evening decline)
    ]
)

# Generator UC parameters (synthetic for case39 10 generators)
# Varied by generator to create meaningful commitment decisions
GEN_UC_PARAMS = [
    # (min_up, min_down, startup_cost, ramp_up_pu, ramp_down_pu, p_min_pu)
    (8, 4, 5000.0, 0.5, 0.5, 0.3),  # G0 - large baseload (bus 30)
    (6, 3, 3000.0, 0.4, 0.4, 0.25),  # G1 (bus 31)
    (6, 3, 3200.0, 0.4, 0.4, 0.25),  # G2 (bus 32)
    (6, 3, 3100.0, 0.4, 0.4, 0.25),  # G3 (bus 33)
    (4, 2, 2000.0, 0.6, 0.6, 0.2),  # G4 (bus 34) - mid-merit
    (6, 3, 3200.0, 0.4, 0.4, 0.25),  # G5 (bus 35)
    (4, 2, 2500.0, 0.5, 0.5, 0.2),  # G6 (bus 36) - mid-merit
    (4, 2, 2300.0, 0.5, 0.5, 0.2),  # G7 (bus 37) - mid-merit
    (2, 1, 1000.0, 0.8, 0.8, 0.15),  # G8 (bus 38) - peaker
    (2, 1, 800.0, 1.0, 1.0, 0.10),  # G9 (bus 39) - peaker
]


def _load_network(case_file: str) -> tuple[pypsa.Network, CaseFrames]:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    cf = CaseFrames(str(DATA_DIR / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net, cf


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute the test and return structured results."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    case_file = Path(network_file).name

    start = time.perf_counter()
    try:
        # 1. Load network
        net, cf = _load_network(case_file)

        # 2. Set up 24-hour snapshots
        snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
        net.set_snapshots(snapshots)

        # Assign snapshot weightings (each hour = 1 hour)
        net.snapshot_weightings.loc[:, "objective"] = 1.0
        net.snapshot_weightings.loc[:, "generators"] = 1.0
        net.snapshot_weightings.loc[:, "stores"] = 1.0

        # 3. Set time-varying load profile
        base_loads = net.loads["p_set"].copy()
        load_profile_df = pd.DataFrame(
            {load: base_loads[load] * LOAD_PROFILE for load in net.loads.index},
            index=snapshots,
        )
        net.loads_t.p_set = load_profile_df

        # 4. Manually assign generator costs (workaround for missing gencost import)
        gencost = cf.gencost.values
        for i, gen_name in enumerate(net.generators.index):
            if i < len(gencost):
                c2 = gencost[i, 4]  # quadratic coefficient
                c1 = gencost[i, 5]  # linear coefficient
                p_operating = net.generators.at[gen_name, "p_set"]
                marginal = c1 + 2 * c2 * p_operating
                net.generators.at[gen_name, "marginal_cost"] = max(marginal, 1.0)

        results["workarounds"].append(
            "Manually assigned marginal_cost from MATPOWER gencost data — "
            "PyPSA pypower importer skips gencost on import."
        )

        # 5. Configure UC parameters (built-in PyPSA attributes)
        for i, gen_name in enumerate(net.generators.index):
            params = GEN_UC_PARAMS[i] if i < len(GEN_UC_PARAMS) else GEN_UC_PARAMS[-1]
            min_up, min_down, startup_cost, ramp_up, ramp_down, p_min_pu = params

            net.generators.at[gen_name, "committable"] = True
            net.generators.at[gen_name, "min_up_time"] = min_up
            net.generators.at[gen_name, "min_down_time"] = min_down
            net.generators.at[gen_name, "start_up_cost"] = startup_cost
            net.generators.at[gen_name, "shut_down_cost"] = startup_cost * 0.1
            net.generators.at[gen_name, "ramp_limit_up"] = ramp_up
            net.generators.at[gen_name, "ramp_limit_down"] = ramp_down
            net.generators.at[gen_name, "p_min_pu"] = p_min_pu

            # Ensure p_nom is set correctly
            if net.generators.at[gen_name, "p_nom"] <= 0:
                net.generators.at[gen_name, "p_nom"] = net.generators.at[gen_name, "p_set"] * 1.5

        # 6. Add reserve requirement via extra_functionality callback
        reserve_margin = 0.10  # 10% reserve over peak load

        def reserve_constraint(network, snapshots):
            """Add spinning reserve constraint: sum of committed capacity >= load + reserve."""
            import xarray as xr

            m = network.model
            # Generator-status variable has dims (snapshot, name)
            gen_status = m.variables["Generator-status"]
            # p_nom as xarray with matching 'name' dimension
            committable_gens = network.generators.index[network.generators["committable"]]
            p_nom_da = xr.DataArray(
                network.generators.loc[committable_gens, "p_nom"].values,
                dims=["name"],
                coords={"name": committable_gens.values},
            )

            # Total committed capacity per snapshot: sum(status_g * p_nom_g) for each t
            committed_capacity = (gen_status * p_nom_da).sum("name")

            # Total load per snapshot
            total_load_series = network.loads_t.p_set.sum(axis=1)
            required = total_load_series.values * (1 + reserve_margin)
            required_da = xr.DataArray(
                required,
                dims=["snapshot"],
                coords={"snapshot": snapshots.values},
            )

            # Reserve constraint: committed_capacity >= required
            m.add_constraints(
                committed_capacity >= required_da,
                name="reserve_requirement",
            )

        # 7. Solve SCUC as MILP
        status, termination = net.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
            extra_functionality=reserve_constraint,
        )

        results["details"]["solver_status"] = status
        results["details"]["termination_condition"] = termination

        # 8. Extract commitment schedule as binary matrix
        # PyPSA stores commitment status in generators_t.status
        if hasattr(net.generators_t, "status") and len(net.generators_t.status) > 0:
            commitment_matrix = net.generators_t.status
            results["details"]["commitment_schedule"] = {
                str(gen): [int(v) for v in commitment_matrix[gen].values]
                for gen in commitment_matrix.columns
            }
            results["details"]["commitment_shape"] = list(commitment_matrix.shape)
        else:
            results["errors"].append("No commitment status in generators_t.status")

        # 9. Extract dispatch
        gen_dispatch = net.generators_t.p
        results["details"]["dispatch_shape"] = list(gen_dispatch.shape)
        results["details"]["total_generation_per_hour"] = [
            float(gen_dispatch.loc[sn].sum()) for sn in snapshots
        ]
        results["details"]["total_load_per_hour"] = [
            float(net.loads_t.p_set.loc[sn].sum()) for sn in snapshots
        ]

        # 10. Validate results
        objective = net.objective if hasattr(net, "objective") else None
        results["details"]["objective"] = float(objective) if objective is not None else None

        # Check MIP gap
        # HiGHS doesn't directly expose gap in PyPSA, but we can check status
        if "optimal" in str(status).lower() or "ok" in str(status).lower():
            results["details"]["mip_gap_satisfied"] = True
        else:
            results["details"]["mip_gap_satisfied"] = False
            results["errors"].append(f"Solver status not optimal: {status} / {termination}")

        # Verify commitment is binary
        if "commitment_schedule" in results["details"]:
            cm = commitment_matrix
            all_binary = ((cm == 0) | (cm == 1)).all().all()
            results["details"]["commitment_is_binary"] = bool(all_binary)
            if not all_binary:
                # Check near-binary (within tolerance)
                near_binary = ((cm < 0.01) | (cm > 0.99)).all().all()
                results["details"]["commitment_near_binary"] = bool(near_binary)

            # Count startups and shutdowns
            startups = 0
            shutdowns = 0
            for gen in cm.columns:
                status_series = cm[gen].values
                for t in range(1, len(status_series)):
                    if status_series[t] > 0.5 and status_series[t - 1] < 0.5:
                        startups += 1
                    elif status_series[t] < 0.5 and status_series[t - 1] > 0.5:
                        shutdowns += 1
            results["details"]["total_startups"] = startups
            results["details"]["total_shutdowns"] = shutdowns

        # Document built-in vs user-assembled constraints
        results["details"]["builtin_constraints"] = [
            "min_up_time",
            "min_down_time",
            "start_up_cost",
            "shut_down_cost",
            "ramp_limit_up",
            "ramp_limit_down",
            "p_min_pu (min stable generation)",
        ]
        results["details"]["user_assembled_constraints"] = [
            "reserve_requirement (via extra_functionality callback)",
        ]

        # 11. Set pass status
        if (
            results["details"].get("mip_gap_satisfied")
            and "commitment_schedule" in results["details"]
        ):
            results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
