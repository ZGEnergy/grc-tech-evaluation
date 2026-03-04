"""
Test B-4: 50 stochastic scenarios, 24-hour multi-period DCPF

Dimension: extensibility
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Tool accepts timeseries programmatically, scenario loop expressible.
Tool: pypsa 1.1.2
Solver: HiGHS (LP)

Strategy: Generate 50 stochastic load scenarios (random perturbations of a base
24-hour profile), solve DC OPF for each scenario, and collect results. This tests
PyPSA's ability to handle multi-period time series programmatically and express
a scenario loop in user code.
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
SOLVER_OPTIONS = {
    "time_limit": 300.0,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,  # Quiet for 50 solves
}

N_SCENARIOS = 50

# Base 24-hour load profile multipliers
LOAD_PROFILE_BASE = np.array(
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
    net.import_from_pypower_ppc(ppc)
    return net, cf


def _generate_scenarios(rng: np.random.Generator, n: int) -> list[np.ndarray]:
    """Generate n stochastic load scenarios.

    Each scenario is a 24-element array of load multipliers, created by adding
    correlated noise to the base load profile. Uses a simple AR(1) process
    to create temporally correlated perturbations.
    """
    scenarios = []
    for _ in range(n):
        # AR(1) noise: each hour's perturbation is correlated with the previous
        noise = np.zeros(24)
        noise[0] = rng.normal(0, 0.03)
        for t in range(1, 24):
            noise[t] = 0.7 * noise[t - 1] + rng.normal(0, 0.03)

        # Apply noise to base profile, clip to stay within feasible generation range
        scenario = np.clip(LOAD_PROFILE_BASE + noise, 0.4, 1.0)
        scenarios.append(scenario)
    return scenarios


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
        # 1. Generate stochastic scenarios
        rng = np.random.default_rng(seed=42)
        scenarios = _generate_scenarios(rng, N_SCENARIOS)

        results["details"]["n_scenarios"] = N_SCENARIOS
        results["details"]["scenario_profile_shape"] = list(scenarios[0].shape)

        # 2. Solve DC OPF for each scenario with 24-hour time series
        scenario_objectives = []
        scenario_total_gen = []
        scenario_solve_times = []
        scenario_statuses = []
        n_converged = 0

        for s_idx, scenario_profile in enumerate(scenarios):
            # Load fresh network for each scenario
            net, cf = _load_network(case_file)

            # Set up 24-hour snapshots
            snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
            net.set_snapshots(snapshots)
            net.snapshot_weightings.loc[:, "objective"] = 1.0
            net.snapshot_weightings.loc[:, "generators"] = 1.0
            net.snapshot_weightings.loc[:, "stores"] = 1.0

            # Time-varying load from scenario profile
            base_loads = net.loads["p_set"].copy()
            load_profile_df = pd.DataFrame(
                {load: base_loads[load] * scenario_profile for load in net.loads.index},
                index=snapshots,
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

            for gen_name in net.generators.index:
                if net.generators.at[gen_name, "p_nom"] <= 0:
                    net.generators.at[gen_name, "p_nom"] = (
                        net.generators.at[gen_name, "p_set"] * 1.5
                    )

            # Solve DC OPF
            s_start = time.perf_counter()
            s_status = net.optimize(
                solver_name=SOLVER_NAME,
                solver_options=SOLVER_OPTIONS,
            )
            s_time = time.perf_counter() - s_start

            scenario_solve_times.append(s_time)

            status_str = str(s_status).lower() if s_status is not None else "unknown"
            scenario_statuses.append(status_str)

            if "ok" in status_str or "optimal" in status_str:
                n_converged += 1
                scenario_objectives.append(float(net.objective))
                total_gen = float(net.generators_t.p.sum().sum())
                scenario_total_gen.append(total_gen)
            else:
                scenario_objectives.append(None)
                scenario_total_gen.append(None)

        # 3. Aggregate results
        total_solve_time = sum(scenario_solve_times)
        valid_objectives = [o for o in scenario_objectives if o is not None]
        valid_gen = [g for g in scenario_total_gen if g is not None]

        results["details"]["n_converged"] = n_converged
        results["details"]["n_failed"] = N_SCENARIOS - n_converged
        results["details"]["total_solve_time_seconds"] = float(total_solve_time)
        results["details"]["avg_solve_time_seconds"] = float(total_solve_time / N_SCENARIOS)
        results["details"]["min_solve_time_seconds"] = float(min(scenario_solve_times))
        results["details"]["max_solve_time_seconds"] = float(max(scenario_solve_times))

        if valid_objectives:
            results["details"]["objective_stats"] = {
                "min": float(min(valid_objectives)),
                "max": float(max(valid_objectives)),
                "mean": float(np.mean(valid_objectives)),
                "std": float(np.std(valid_objectives)),
            }
        if valid_gen:
            results["details"]["total_gen_stats"] = {
                "min": float(min(valid_gen)),
                "max": float(max(valid_gen)),
                "mean": float(np.mean(valid_gen)),
                "std": float(np.std(valid_gen)),
            }

        # Document the approach
        results["details"]["approach"] = (
            "50 independent DC OPF solves, each with 24-hour multi-period snapshots. "
            "Stochastic load scenarios generated via AR(1) perturbations of a base "
            "diurnal profile. Each scenario: load network, set snapshots, assign "
            "time-varying p_set, solve. Results collected in Python lists/arrays."
        )
        results["details"]["timeseries_programmatic"] = True
        results["details"]["scenario_loop_expressible"] = True

        # Pass if majority of scenarios converged
        if n_converged >= N_SCENARIOS * 0.95:
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
