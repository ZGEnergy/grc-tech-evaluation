"""
Test B-4: Stochastic Wrapping — Generate 20 scenarios with correlated load/renewable
perturbations by resource type, solve 12hr multi-period DCOPF per scenario, collect
prices and dispatch.

Dimension: extensibility
Network: TINY (case39)
Pass condition: Tool accepts timeseries inputs programmatically (not from config files
    only). Scenario loop is expressible without excessive per-scenario overhead. Results
    (prices, dispatch) are collectable in a structured format.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")

# HiGHS solver settings per solver-config.md
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,  # Suppress per-scenario solver output
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

    # Parse gencost and set marginal_cost
    gencost = cf.gencost.values
    rng = np.random.default_rng(seed=99)
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])
            if cost_type == 2 and n_coeffs >= 2:
                c1 = float(cost_row[4 + n_coeffs - 2])
                # Perturbation to break degeneracy
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


def _add_renewables(n, snapshots):
    """Add wind and solar generators with time-varying profiles."""
    # Add wind at bus 3 and solar at bus 7
    n.add("Generator", "Wind_1", bus="3", p_nom=200.0, marginal_cost=0.0, carrier="wind")
    n.add("Generator", "Solar_1", bus="7", p_nom=150.0, marginal_cost=0.0, carrier="solar")

    # Base profiles: wind with moderate variability, solar with diurnal pattern
    hours = np.arange(N_HOURS)
    wind_profile = 0.3 + 0.15 * np.sin(2 * np.pi * hours / 24)
    solar_profile = np.clip(0.5 * np.sin(np.pi * (hours - 4) / 12), 0, 1)

    # Build a full p_max_pu DataFrame; existing generators default to 1.0
    p_max_pu = pd.DataFrame(1.0, index=snapshots, columns=n.generators.index)
    p_max_pu["Wind_1"] = wind_profile
    p_max_pu["Solar_1"] = solar_profile
    n.generators_t.p_max_pu = p_max_pu

    return wind_profile, solar_profile


def _generate_scenarios(rng, gen_types, wind_base, solar_base, n_scenarios):
    """Generate correlated perturbations, independent by resource type."""
    scenarios = []
    for s in range(n_scenarios):
        # Independent perturbation factor per resource type
        load_factor = rng.uniform(0.92, 1.08)  # +/- 8% load perturbation
        baseload_factor = rng.uniform(0.97, 1.03)  # Small perturbation for baseload
        intermediate_factor = rng.uniform(0.93, 1.07)
        peaker_factor = rng.uniform(0.90, 1.10)  # Larger for peakers
        wind_factor = rng.uniform(0.70, 1.30)  # +/- 30% wind perturbation
        solar_factor = rng.uniform(0.80, 1.20)  # +/- 20% solar perturbation

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
    """Execute stochastic wrapping test and return structured results."""
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

        # Set time-varying loads (constant for base, scaled per scenario)
        base_loads = n_base.loads["p_set"].copy()
        load_df = pd.DataFrame(
            {load_idx: base_loads[load_idx] for load_idx in n_base.loads.index},
            index=snapshots,
        )
        n_base.loads_t.p_set = load_df

        # Add renewables
        wind_base, solar_base = _add_renewables(n_base, snapshots)

        # Classify generators by resource type
        gen_types = _classify_generators(n_base)

        # 2. Generate 20 scenarios
        rng = np.random.default_rng(seed=RNG_SEED)
        scenarios = _generate_scenarios(rng, gen_types, wind_base, solar_base, N_SCENARIOS)

        # 3. Solve each scenario
        all_lmps = []
        all_dispatch = []
        all_objectives = []
        scenario_times = []

        results["workarounds"].append(
            "Manually set marginal_cost from gencost data (PPC importer does not import gencost)"
        )

        for s_idx, scenario in enumerate(scenarios):
            # Copy network for this scenario
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

            # Apply generator p_nom perturbations by resource type
            for gen_idx in n.generators.index:
                if gen_idx in gen_types:
                    gtype = gen_types[gen_idx]
                    if gtype in scenario["gen_factors"]:
                        factor = scenario["gen_factors"][gtype]
                        p_nom = n_base.generators.loc[gen_idx, "p_nom"]
                        n.generators.loc[gen_idx, "p_nom"] = p_nom * factor

            # Apply renewable profiles for this scenario
            p_max_pu = pd.DataFrame(1.0, index=snapshots, columns=n.generators.index)
            p_max_pu["Wind_1"] = scenario["wind_profile"]
            p_max_pu["Solar_1"] = scenario["solar_profile"]
            n.generators_t.p_max_pu = p_max_pu

            # Solve DCOPF
            t0 = time.perf_counter()
            status = n.optimize(solver_name=SOLVER_NAME, solver_options=SOLVER_OPTIONS)
            t1 = time.perf_counter()
            scenario_times.append(t1 - t0)

            converged = "ok" in str(status).lower() or "optimal" in str(status).lower()
            if not converged:
                results["errors"].append(f"Scenario {s_idx} failed: {status}")
                continue

            # Collect results
            lmps = n.buses_t.marginal_price.copy()
            lmps["scenario"] = s_idx
            all_lmps.append(lmps)

            dispatch = n.generators_t.p.copy()
            dispatch["scenario"] = s_idx
            all_dispatch.append(dispatch)

            all_objectives.append(float(n.objective))

        elapsed_total = time.perf_counter() - start_total

        # 4. Aggregate results
        n_solved = len(all_objectives)
        if n_solved == 0:
            results["errors"].append("No scenarios converged")
            results["wall_clock_seconds"] = elapsed_total
            return results

        # Combine into structured DataFrames
        lmp_df = pd.concat(all_lmps, ignore_index=True)
        dispatch_df = pd.concat(all_dispatch, ignore_index=True)

        # Summary statistics
        obj_arr = np.array(all_objectives)
        time_arr = np.array(scenario_times)

        # LMP statistics across scenarios (excluding 'scenario' column)
        lmp_cols = [c for c in lmp_df.columns if c != "scenario"]
        lmp_values = lmp_df[lmp_cols].values

        # Dispatch statistics
        dispatch_cols = [c for c in dispatch_df.columns if c != "scenario"]
        dispatch_values = dispatch_df[dispatch_cols].values

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
            "lmp_mean": float(np.nanmean(lmp_values)),
            "lmp_std": float(np.nanstd(lmp_values)),
            "lmp_min": float(np.nanmin(lmp_values)),
            "lmp_max": float(np.nanmax(lmp_values)),
            "dispatch_total_mean_MW": float(dispatch_values.sum(axis=1).mean()),
            "result_format": "pandas DataFrame with scenario column",
            "api_mechanism": (
                "n.copy() for per-scenario network, "
                "direct DataFrame assignment for timeseries, "
                "n.optimize() per scenario"
            ),
            "generator_types": gen_types,
            "renewable_generators_added": ["Wind_1", "Solar_1"],
        }

        results["wall_clock_seconds"] = elapsed_total

        # Pass condition: all scenarios solved, results in structured format
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
