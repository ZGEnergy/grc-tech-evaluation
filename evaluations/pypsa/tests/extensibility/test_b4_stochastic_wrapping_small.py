"""
Test B-4: Stochastic Wrapping -- Generate 20 scenarios with correlated load/renewable
perturbations by resource type, solve 12hr multi-period DCOPF per scenario, collect
prices and dispatch.

Dimension: extensibility
Network: SMALL (ACTIVSg 2000-bus)
Pass condition: Tool accepts timeseries inputs programmatically. Scenario loop
    expressible without excessive per-scenario overhead. Results collectable in
    structured format.
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

SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,
}

N_SCENARIOS = 20
N_HOURS = 12
RNG_SEED = 42


def _load_network_with_costs(case_path: str):
    """Load MATPOWER .m file and set marginal costs from gencost."""
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
    rng = np.random.default_rng(seed=99)
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])
            if cost_type == 2 and n_coeffs >= 2:
                c1 = float(cost_row[4 + n_coeffs - 2])
                perturbation = rng.uniform(-0.1, 0.1) * c1
                net.generators.loc[gen_idx, "marginal_cost"] = c1 + perturbation

    return net


def _classify_generators(n):
    """Classify generators by cost quartile as resource types."""
    costs = n.generators["marginal_cost"].sort_values()
    q25 = costs.quantile(0.25)
    q75 = costs.quantile(0.75)
    types = {}
    for gen in n.generators.index:
        mc = n.generators.loc[gen, "marginal_cost"]
        if mc <= q25:
            types[gen] = "baseload"
        elif mc >= q75:
            types[gen] = "peaker"
        else:
            types[gen] = "intermediate"
    return types


def _generate_scenarios(rng, wind_base, solar_base, n_scenarios):
    """Generate correlated perturbations, independent by resource type."""
    scenarios = []
    for s in range(n_scenarios):
        load_factor = rng.uniform(0.92, 1.08)
        baseload_factor = rng.uniform(0.97, 1.03)
        intermediate_factor = rng.uniform(0.93, 1.07)
        peaker_factor = rng.uniform(0.90, 1.10)
        wind_factor = rng.uniform(0.70, 1.30)
        solar_factor = rng.uniform(0.80, 1.20)

        scenarios.append(
            {
                "load_factor": load_factor,
                "gen_factors": {
                    "baseload": baseload_factor,
                    "intermediate": intermediate_factor,
                    "peaker": peaker_factor,
                },
                "wind_profile": np.clip(wind_base * wind_factor, 0, 1),
                "solar_profile": np.clip(solar_base * solar_factor, 0, 1),
            }
        )
    return scenarios


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute stochastic wrapping test on 2000-bus and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start_total = time.perf_counter()
    try:
        # 1. Load base network
        n_base = _load_network_with_costs(network_file)

        # Set up 12 hourly snapshots
        snapshots = pd.date_range("2024-01-01", periods=N_HOURS, freq="h")
        n_base.set_snapshots(snapshots)

        # Set time-varying loads
        base_loads = n_base.loads["p_set"].copy()
        load_df = pd.DataFrame(
            {load_idx: base_loads[load_idx] for load_idx in n_base.loads.index},
            index=snapshots,
        )
        n_base.loads_t.p_set = load_df

        # Add renewables at buses with generators
        gen_buses = n_base.generators["bus"].unique()
        wind_bus = gen_buses[0] if len(gen_buses) > 0 else n_base.buses.index[0]
        solar_bus = gen_buses[min(5, len(gen_buses) - 1)] if len(gen_buses) > 5 else wind_bus

        n_base.add(
            "Generator",
            "Wind_1",
            bus=wind_bus,
            p_nom=500.0,
            marginal_cost=0.0,
            carrier="wind",
        )
        n_base.add(
            "Generator",
            "Solar_1",
            bus=solar_bus,
            p_nom=400.0,
            marginal_cost=0.0,
            carrier="solar",
        )

        hours = np.arange(N_HOURS)
        wind_base = 0.3 + 0.15 * np.sin(2 * np.pi * hours / 24)
        solar_base = np.clip(0.5 * np.sin(np.pi * (hours - 4) / 12), 0, 1)

        p_max_pu = pd.DataFrame(1.0, index=snapshots, columns=n_base.generators.index)
        p_max_pu["Wind_1"] = wind_base
        p_max_pu["Solar_1"] = solar_base
        n_base.generators_t.p_max_pu = p_max_pu

        # Classify generators
        gen_types = _classify_generators(n_base)

        # 2. Generate scenarios
        rng = np.random.default_rng(seed=RNG_SEED)
        scenarios = _generate_scenarios(rng, wind_base, solar_base, N_SCENARIOS)

        # 3. Solve each scenario
        all_objectives = []
        scenario_times = []
        all_lmp_stats = []

        results["workarounds"].append(
            "Manually set marginal_cost from gencost data (PPC importer does not import gencost)"
        )

        for s_idx, scenario in enumerate(scenarios):
            n = n_base.copy()

            # Apply load perturbation
            load_scenario = pd.DataFrame(
                {
                    load_idx: base_loads[load_idx] * scenario["load_factor"]
                    for load_idx in n.loads.index
                },
                index=snapshots,
            )
            n.loads_t.p_set = load_scenario

            # Apply generator p_nom perturbations
            for gen_idx in n.generators.index:
                if gen_idx in gen_types:
                    gtype = gen_types[gen_idx]
                    if gtype in scenario["gen_factors"]:
                        factor = scenario["gen_factors"][gtype]
                        p_nom = n_base.generators.loc[gen_idx, "p_nom"]
                        n.generators.loc[gen_idx, "p_nom"] = p_nom * factor

            # Apply renewable profiles
            p_max_pu_s = pd.DataFrame(1.0, index=snapshots, columns=n.generators.index)
            p_max_pu_s["Wind_1"] = scenario["wind_profile"]
            p_max_pu_s["Solar_1"] = scenario["solar_profile"]
            n.generators_t.p_max_pu = p_max_pu_s

            # Solve
            t0 = time.perf_counter()
            status = n.optimize(solver_name=SOLVER_NAME, solver_options=SOLVER_OPTIONS)
            t1 = time.perf_counter()
            scenario_times.append(t1 - t0)

            converged = "ok" in str(status).lower() or "optimal" in str(status).lower()
            if not converged:
                results["errors"].append(f"Scenario {s_idx} failed: {status}")
                continue

            all_objectives.append(float(n.objective))
            lmps = n.buses_t.marginal_price
            all_lmp_stats.append(
                {
                    "mean": float(lmps.values.mean()),
                    "min": float(lmps.values.min()),
                    "max": float(lmps.values.max()),
                }
            )

        elapsed_total = time.perf_counter() - start_total

        # 4. Aggregate results
        n_solved = len(all_objectives)
        if n_solved == 0:
            results["errors"].append("No scenarios converged")
            results["wall_clock_seconds"] = elapsed_total
            return results

        obj_arr = np.array(all_objectives)
        time_arr = np.array(scenario_times)

        results["details"] = {
            "n_scenarios_requested": N_SCENARIOS,
            "n_scenarios_solved": n_solved,
            "n_hours": N_HOURS,
            "solver": SOLVER_NAME,
            "total_time_s": elapsed_total,
            "solve_time_total_s": float(time_arr.sum()),
            "solve_time_mean_s": float(time_arr.mean()),
            "solve_time_std_s": float(time_arr.std()),
            "solve_time_min_s": float(time_arr.min()),
            "solve_time_max_s": float(time_arr.max()),
            "objective_mean": float(obj_arr.mean()),
            "objective_std": float(obj_arr.std()),
            "objective_min": float(obj_arr.min()),
            "objective_max": float(obj_arr.max()),
            "lmp_stats_sample": all_lmp_stats[:3],
            "api_mechanism": (
                "n.copy() for per-scenario network, "
                "direct DataFrame assignment for timeseries, "
                "n.optimize() per scenario"
            ),
            "network_stats": {
                "buses": len(n_base.buses),
                "generators": len(n_base.generators),
                "lines": len(n_base.lines),
            },
            "renewable_generators_added": ["Wind_1", "Solar_1"],
        }

        results["wall_clock_seconds"] = elapsed_total

        if n_solved == N_SCENARIOS:
            results["status"] = "pass"
        elif n_solved >= N_SCENARIOS * 0.9:
            results["status"] = "qualified_pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["wall_clock_seconds"] = time.perf_counter() - start_total

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
