"""
Test C-4: SCUC 24-hour at scale (SMALL — 2000-bus network)

Dimension: scalability
Network: SMALL (case_ACTIVSg2000 — 2,000 buses)
Pass condition: Solves to feasibility (MIP gap <= 1%). Record wall_clock, MIP_gap.
Tool: pypsa 1.1.2
Solver: HiGHS (MILP)

Note: PyPSA pypower importer does NOT import gencost — manual cost assignment required.
      UC parameters are synthetically assigned by generator index since MATPOWER cases
      do not include commitment data.
"""

from __future__ import annotations

import json
import resource
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"

SOLVERS = [
    (
        "highs",
        {
            "time_limit": 600.0,
            "mip_rel_gap": 0.01,
            "presolve": "on",
            "threads": 4,
            "output_flag": True,
            "primal_feasibility_tolerance": 1e-4,
            "mip_feasibility_tolerance": 1e-4,
        },
    ),
    (
        "scip",
        {
            "limits/time": 600.0,
            "limits/gap": 0.01,
        },
    ),
]

# 24-hour load profile multipliers
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
    net.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=9999.0)
    return net, cf


def run() -> dict:
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "peak_memory_mb": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load SMALL network
        net, cf = _load_network("case_ACTIVSg2000.m")

        results["details"]["bus_count"] = len(net.buses)
        results["details"]["line_count"] = len(net.lines)
        results["details"]["transformer_count"] = len(net.transformers)
        results["details"]["generator_count"] = len(net.generators)

        # 2. Set up 24-hour snapshots
        snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
        net.set_snapshots(snapshots)
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

        # 4. Assign generator costs from gencost
        gencost = cf.gencost.values
        for i, gen_name in enumerate(net.generators.index):
            if i < len(gencost):
                n_coeffs = int(gencost[i, 3])
                if n_coeffs >= 2:
                    c1 = gencost[i, 4 + n_coeffs - 2]
                    c2 = gencost[i, 4] if n_coeffs >= 3 else 0.0
                    p_op = net.generators.at[gen_name, "p_set"]
                    marginal = c1 + 2 * c2 * abs(p_op)
                    net.generators.at[gen_name, "marginal_cost"] = max(marginal, 1.0)
                else:
                    net.generators.at[gen_name, "marginal_cost"] = 10.0 + i * 0.5
            else:
                net.generators.at[gen_name, "marginal_cost"] = 10.0 + i * 0.5

        results["workarounds"].append(
            "Manually assigned marginal_cost from MATPOWER gencost — "
            "PyPSA pypower importer skips gencost on import."
        )

        # 5. Configure UC parameters
        # Classify generators by relative size for UC parameter assignment
        p_noms = net.generators["p_nom"].values
        p_max = p_noms.max() if len(p_noms) > 0 else 1.0

        for i, gen_name in enumerate(net.generators.index):
            p_nom = net.generators.at[gen_name, "p_nom"]
            if p_nom <= 0:
                p_nom = max(net.generators.at[gen_name, "p_set"] * 1.5, 10.0)
                net.generators.at[gen_name, "p_nom"] = p_nom

            # Size-based UC classification
            size_frac = p_nom / p_max

            net.generators.at[gen_name, "committable"] = True

            if size_frac > 0.3:
                # Large baseload
                net.generators.at[gen_name, "min_up_time"] = 4
                net.generators.at[gen_name, "min_down_time"] = 2
                net.generators.at[gen_name, "start_up_cost"] = 5000.0
                net.generators.at[gen_name, "shut_down_cost"] = 500.0
                net.generators.at[gen_name, "ramp_limit_up"] = 0.6
                net.generators.at[gen_name, "ramp_limit_down"] = 0.6
                net.generators.at[gen_name, "p_min_pu"] = 0.2
            elif size_frac > 0.1:
                # Mid-merit
                net.generators.at[gen_name, "min_up_time"] = 2
                net.generators.at[gen_name, "min_down_time"] = 1
                net.generators.at[gen_name, "start_up_cost"] = 2000.0
                net.generators.at[gen_name, "shut_down_cost"] = 200.0
                net.generators.at[gen_name, "ramp_limit_up"] = 0.8
                net.generators.at[gen_name, "ramp_limit_down"] = 0.8
                net.generators.at[gen_name, "p_min_pu"] = 0.15
            else:
                # Peaker
                net.generators.at[gen_name, "min_up_time"] = 1
                net.generators.at[gen_name, "min_down_time"] = 1
                net.generators.at[gen_name, "start_up_cost"] = 500.0
                net.generators.at[gen_name, "shut_down_cost"] = 50.0
                net.generators.at[gen_name, "ramp_limit_up"] = 1.0
                net.generators.at[gen_name, "ramp_limit_down"] = 1.0
                net.generators.at[gen_name, "p_min_pu"] = 0.1

        results["workarounds"].append(
            "Synthetically assigned UC parameters (min_up/down_time, startup/shutdown cost, "
            "ramp limits, p_min_pu) by generator size classification — MATPOWER cases lack "
            "commitment data."
        )

        # 6. Solve SCUC — try each solver until one succeeds
        import copy

        net_template = copy.deepcopy(net)
        status = None
        termination = None
        solver_used = None

        for solver_name, solver_options in SOLVERS:
            net = copy.deepcopy(net_template)
            solve_start = time.perf_counter()
            try:
                status, termination = net.optimize(
                    solver_name=solver_name,
                    solver_options=solver_options,
                )
                solve_time = time.perf_counter() - solve_start
                results["details"]["solve_time_seconds"] = solve_time
                results["details"]["solver_status"] = str(status)
                results["details"]["termination_condition"] = str(termination)
                results["details"]["solver_used"] = solver_name
                solver_used = solver_name
                # If we got a valid status, break
                if "ok" in str(status).lower():
                    break
            except Exception as e:
                solve_time = time.perf_counter() - solve_start
                results["details"][f"{solver_name}_error"] = f"{type(e).__name__}: {e}"
                results["details"][f"{solver_name}_time"] = solve_time
                continue

        if solver_used is None:
            results["errors"].append("All solvers failed")
            results["status"] = "fail"

        # 7. Extract results
        objective = net.objective if hasattr(net, "objective") else None
        results["details"]["objective"] = float(objective) if objective is not None else None

        # Commitment schedule
        if hasattr(net.generators_t, "status") and len(net.generators_t.status) > 0:
            cm = net.generators_t.status
            results["details"]["commitment_shape"] = list(cm.shape)

            # Count startups/shutdowns
            startups = 0
            shutdowns = 0
            for gen in cm.columns:
                vals = cm[gen].values
                for t in range(1, len(vals)):
                    if vals[t] > 0.5 and vals[t - 1] < 0.5:
                        startups += 1
                    elif vals[t] < 0.5 and vals[t - 1] > 0.5:
                        shutdowns += 1
            results["details"]["total_startups"] = startups
            results["details"]["total_shutdowns"] = shutdowns

            # Generators committed per hour (mean)
            committed_per_hour = (cm > 0.5).sum(axis=1)
            results["details"]["avg_committed_generators"] = float(committed_per_hour.mean())
            results["details"]["min_committed_generators"] = int(committed_per_hour.min())
            results["details"]["max_committed_generators"] = int(committed_per_hour.max())

        # Dispatch summary
        gen_dispatch = net.generators_t.p
        results["details"]["dispatch_shape"] = list(gen_dispatch.shape)
        results["details"]["total_gen_per_hour"] = [
            float(gen_dispatch.loc[sn].sum()) for sn in snapshots
        ]

        # MIP gap assessment
        import math

        obj_val = results["details"]["objective"]
        has_solution = obj_val is not None and not math.isinf(obj_val)

        if has_solution and "ok" in str(status).lower():
            if "optimal" in str(termination).lower():
                results["details"]["mip_gap_satisfied"] = True
                results["status"] = "pass"
            elif "time_limit" in str(termination).lower():
                # Hit time limit but found a feasible solution
                results["details"]["mip_gap_satisfied"] = False
                results["status"] = "qualified_pass"
                results["errors"].append(
                    f"Solver hit time limit but found feasible solution: objective={obj_val}"
                )
            else:
                results["details"]["mip_gap_satisfied"] = False
                results["status"] = "qualified_pass"
                results["errors"].append(f"Solver status: {status} / {termination}")
        elif "ok" in str(status).lower() and "time_limit" in str(termination).lower():
            # Hit time limit without finding a feasible solution
            results["details"]["mip_gap_satisfied"] = False
            results["status"] = "fail"
            results["errors"].append(
                f"Solver hit time limit without finding a feasible solution: "
                f"status={status}, termination={termination}"
            )
        else:
            results["details"]["mip_gap_satisfied"] = False
            results["status"] = "fail"
            results["errors"].append(f"Solver status: {status} / {termination}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        results["peak_memory_mb"] = mem_after / 1024.0

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
