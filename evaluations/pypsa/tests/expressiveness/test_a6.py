"""
Test A-6: Fix commitment from A-5 SCUC, solve SCED as LP

Dimension: expressiveness
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Dispatch extractable, UC and ED cleanly separable as two-stage workflow.
Tool: pypsa 1.1.2
Solver: HiGHS (LP for SCED stage)

Strategy:
1. Run SCUC (A-5) to get the binary commitment schedule.
2. Fix commitment by setting p_min_pu to 0 for decommitted generators and
   removing committable flag (converting MILP to LP).
3. Solve economic dispatch as LP with fixed commitment.
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

# HiGHS solver settings
SOLVER_NAME = "highs"
SOLVER_OPTIONS_MILP = {
    "time_limit": 300.0,
    "mip_rel_gap": 0.01,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}
SOLVER_OPTIONS_LP = {
    "time_limit": 300.0,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

# 24-hour load profile multipliers (same as A-5)
LOAD_PROFILE = np.array(
    [
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
        0.93,
        0.87,
        0.90,
        0.91,
        0.99,
        1.00,
        0.96,
        0.91,
        0.83,
        0.73,
        0.63,
    ]
)

# Generator UC parameters (same as A-5)
GEN_UC_PARAMS = [
    (8, 4, 5000.0, 0.5, 0.5, 0.3),
    (6, 3, 3000.0, 0.4, 0.4, 0.25),
    (6, 3, 3200.0, 0.4, 0.4, 0.25),
    (6, 3, 3100.0, 0.4, 0.4, 0.25),
    (4, 2, 2000.0, 0.6, 0.6, 0.2),
    (6, 3, 3200.0, 0.4, 0.4, 0.25),
    (4, 2, 2500.0, 0.5, 0.5, 0.2),
    (4, 2, 2300.0, 0.5, 0.5, 0.2),
    (2, 1, 1000.0, 0.8, 0.8, 0.15),
    (2, 1, 800.0, 1.0, 1.0, 0.10),
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


def _setup_24h_network(net: pypsa.Network, cf: CaseFrames) -> pd.DatetimeIndex:
    """Configure the network for 24-hour multi-period operation (same as A-5)."""
    _snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
    net.set_snapshots(_snapshots)

    net.snapshot_weightings.loc[:, "objective"] = 1.0
    net.snapshot_weightings.loc[:, "generators"] = 1.0
    net.snapshot_weightings.loc[:, "stores"] = 1.0

    # Time-varying load
    base_loads = net.loads["p_set"].copy()
    load_profile_df = pd.DataFrame(
        {load: base_loads[load] * LOAD_PROFILE for load in net.loads.index},
        index=_snapshots,
    )
    net.loads_t.p_set = load_profile_df

    # Assign generator costs
    gencost = cf.gencost.values
    for i, gen_name in enumerate(net.generators.index):
        if i < len(gencost):
            c2 = gencost[i, 4]
            c1 = gencost[i, 5]
            p_operating = net.generators.at[gen_name, "p_set"]
            marginal = c1 + 2 * c2 * p_operating
            net.generators.at[gen_name, "marginal_cost"] = max(marginal, 1.0)

    # UC parameters
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

        if net.generators.at[gen_name, "p_nom"] <= 0:
            net.generators.at[gen_name, "p_nom"] = net.generators.at[gen_name, "p_set"] * 1.5

    return _snapshots


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
        # === Stage 1: SCUC (MILP) to get commitment schedule ===
        net, cf = _load_network(case_file)
        _setup_24h_network(net, cf)

        scuc_start = time.perf_counter()
        status_scuc, term_scuc = net.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS_MILP,
        )
        scuc_time = time.perf_counter() - scuc_start

        results["details"]["scuc_status"] = str(status_scuc)
        results["details"]["scuc_termination"] = str(term_scuc)
        results["details"]["scuc_wall_seconds"] = float(scuc_time)
        results["details"]["scuc_objective"] = float(net.objective)

        # Extract commitment schedule from SCUC
        commitment_matrix = net.generators_t.status.copy()
        scuc_dispatch = net.generators_t.p.copy()

        results["details"]["commitment_shape"] = list(commitment_matrix.shape)

        # === Stage 2: SCED (LP) with fixed commitment ===
        # Reload network fresh to avoid any solver state contamination
        net2, cf2 = _load_network(case_file)
        snapshots2 = _setup_24h_network(net2, cf2)

        # Fix commitment: for each snapshot, if a generator was OFF in SCUC,
        # set its p_max_pu to 0 for that hour. If ON, keep original limits.
        # Remove committable flag to make it an LP.
        p_max_pu_df = pd.DataFrame(
            1.0,
            index=snapshots2,
            columns=net2.generators.index,
        )

        for gen_name in net2.generators.index:
            # Disable UC (makes it LP)
            net2.generators.at[gen_name, "committable"] = False

            if gen_name in commitment_matrix.columns:
                for sn in snapshots2:
                    if commitment_matrix.at[sn, gen_name] < 0.5:
                        # Generator is OFF at this hour — force output to zero
                        p_max_pu_df.at[sn, gen_name] = 0.0
                    else:
                        # Generator is ON — enforce minimum stable generation
                        pass  # p_min_pu already set in static data

        # Set time-varying p_max_pu to enforce commitment
        net2.generators_t.p_max_pu = p_max_pu_df

        # Also set time-varying p_min_pu for committed generators
        p_min_pu_df = pd.DataFrame(
            0.0,
            index=snapshots2,
            columns=net2.generators.index,
        )
        for i, gen_name in enumerate(net2.generators.index):
            params = GEN_UC_PARAMS[i] if i < len(GEN_UC_PARAMS) else GEN_UC_PARAMS[-1]
            p_min_pu_static = params[5]
            if gen_name in commitment_matrix.columns:
                for sn in snapshots2:
                    if commitment_matrix.at[sn, gen_name] >= 0.5:
                        p_min_pu_df.at[sn, gen_name] = p_min_pu_static
                    else:
                        p_min_pu_df.at[sn, gen_name] = 0.0

        net2.generators_t.p_min_pu = p_min_pu_df

        # Solve SCED as LP
        sced_start = time.perf_counter()
        status_sced, term_sced = net2.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS_LP,
        )
        sced_time = time.perf_counter() - sced_start

        results["details"]["sced_status"] = str(status_sced)
        results["details"]["sced_termination"] = str(term_sced)
        results["details"]["sced_wall_seconds"] = float(sced_time)
        results["details"]["sced_objective"] = float(net2.objective)

        # Extract SCED dispatch
        sced_dispatch = net2.generators_t.p

        # Compare SCUC vs SCED dispatch
        dispatch_diff = (sced_dispatch - scuc_dispatch).abs()
        results["details"]["max_dispatch_diff_mw"] = float(dispatch_diff.max().max())
        results["details"]["mean_dispatch_diff_mw"] = float(dispatch_diff.mean().mean())

        # Verify SCED respects commitment (OFF generators have zero dispatch)
        commitment_respected = True
        for gen_name in net2.generators.index:
            if gen_name in commitment_matrix.columns:
                for sn in snapshots2:
                    if commitment_matrix.at[sn, gen_name] < 0.5:
                        if abs(sced_dispatch.at[sn, gen_name]) > 1e-6:
                            commitment_respected = False
                            break

        results["details"]["commitment_respected"] = commitment_respected

        # Extract LMPs from SCED
        lmps = net2.buses_t.marginal_price
        if len(lmps) > 0:
            results["details"]["sced_lmp_range"] = [
                float(lmps.min().min()),
                float(lmps.max().max()),
            ]
            results["details"]["sced_lmp_mean"] = float(lmps.mean().mean())

        # SCED total generation per hour
        results["details"]["sced_gen_per_hour"] = [
            float(sced_dispatch.loc[sn].sum()) for sn in snapshots2
        ]

        # Document two-stage separation
        results["details"]["separation_method"] = (
            "Stage 1: SCUC with committable=True (MILP). "
            "Stage 2: Reload network, set committable=False, "
            "fix commitment via time-varying p_max_pu=0 for OFF generators. "
            "SCED solves as LP."
        )
        results["details"]["scuc_is_milp"] = True
        results["details"]["sced_is_lp"] = True

        # Set pass status
        if "ok" in str(status_sced).lower() or "optimal" in str(status_sced).lower():
            results["status"] = "pass"

        results["workarounds"].append(
            "Manually assigned marginal_cost from MATPOWER gencost data — "
            "PyPSA pypower importer skips gencost on import (same as A-3)."
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
