"""
Test B-4: Stochastic Scenario Wrap (stochastic_scenario_wrap)

Dimension: extensibility
Network: SMALL (ACTIVSg 2000, case_ACTIVSg2000.m)
Pass condition: Tool accepts timeseries inputs programmatically (not from config files
  only). 20-scenario loop completes. Record per-scenario time and cost statistics.
Tool: PyPSA 1.1.2
"""

import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m")

N_SCENARIOS = 20
N_HOURS = 12
WIND_P_NOM = 200.0  # MW
SOLAR_P_NOM = 150.0  # MW
RANDOM_SEED = 42

# Solver configuration (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,
}


def load_base_network(network_file: str):
    """Load ACTIVSg2000 and set up generators and snapshots."""
    import pandas as pd
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    n = pypsa.Network()
    n.set_snapshots(pd.date_range("2024-01-01", periods=N_HOURS, freq="h"))
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=1.0)

    # Assign differentiated marginal costs
    gen_names = sorted(n.generators.index)
    n_gens = len(gen_names)
    costs = np.linspace(10, 100, n_gens)
    for gen_name, cost in zip(gen_names, costs):
        n.generators.at[gen_name, "marginal_cost"] = float(cost)

    # Add wind and solar generators
    wind_bus = n.buses.index[5]
    solar_bus = n.buses.index[6]
    n.add(
        "Generator",
        "Wind",
        bus=wind_bus,
        p_nom=WIND_P_NOM,
        marginal_cost=0.0,
        p_max_pu=0.3,
        carrier="wind",
    )
    n.add(
        "Generator",
        "Solar",
        bus=solar_bus,
        p_nom=SOLAR_P_NOM,
        marginal_cost=0.0,
        p_max_pu=0.2,
        carrier="solar",
    )

    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute stochastic scenario loop: 20 scenarios × 12-hour DC OPF on 2k-bus network.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        rng = np.random.default_rng(RANDOM_SEED)

        # Load base network once to get structure
        print("Loading base 2k network...")
        n_base = load_base_network(network_file)
        snapshots = n_base.snapshots

        n_buses = len(n_base.buses)
        n_gens = len(n_base.generators)
        print(f"Loaded: {n_buses} buses, {n_gens} generators (including Wind/Solar)")

        results["details"]["n_buses"] = n_buses
        results["details"]["n_generators"] = n_gens
        results["details"]["n_scenarios"] = N_SCENARIOS
        results["details"]["n_hours"] = N_HOURS

        # Generate 20 scenarios
        scenarios = []
        for s in range(N_SCENARIOS):
            load_mult = rng.uniform(0.85, 1.05, size=N_HOURS)
            wind_cf = rng.uniform(0.1, 0.7, size=N_HOURS)
            solar_cf = rng.uniform(0.0, 0.5, size=N_HOURS)
            scenarios.append(
                {
                    "load_mult": load_mult,
                    "wind_cf": wind_cf,
                    "solar_cf": solar_cf,
                }
            )

        # Baseline load p_set for scaling
        base_load_p_set = n_base.loads.p_set.copy()

        scenario_results = []
        per_scenario_times = []
        n_failed = 0

        for s_idx, scenario in enumerate(scenarios):
            sc_start = time.perf_counter()
            try:
                import pypsa
                from matpowercaseframes import CaseFrames

                # Re-load network for each scenario
                cf = CaseFrames(network_file)
                ppc_s = {
                    "version": "2",
                    "baseMVA": float(cf.baseMVA),
                    "bus": cf.bus.values,
                    "gen": cf.gen.values,
                    "branch": cf.branch.values,
                }
                n_s = pypsa.Network()
                n_s.set_snapshots(snapshots)
                n_s.import_from_pypower_ppc(ppc_s, overwrite_zero_s_nom=1.0)

                # Assign differentiated marginal costs
                gen_names_s = sorted(n_s.generators.index)
                costs_s = np.linspace(10, 100, len(gen_names_s))
                for gen_name, cost in zip(gen_names_s, costs_s):
                    n_s.generators.at[gen_name, "marginal_cost"] = float(cost)

                # Add wind and solar
                wind_bus = n_s.buses.index[5]
                solar_bus = n_s.buses.index[6]
                n_s.add(
                    "Generator",
                    "Wind",
                    bus=wind_bus,
                    p_nom=WIND_P_NOM,
                    marginal_cost=0.0,
                    carrier="wind",
                )
                n_s.add(
                    "Generator",
                    "Solar",
                    bus=solar_bus,
                    p_nom=SOLAR_P_NOM,
                    marginal_cost=0.0,
                    carrier="solar",
                )

                # Set per-scenario timeseries
                load_mult_series = scenario["load_mult"]
                for load_name in n_s.loads.index:
                    if load_name in base_load_p_set.index:
                        base_p = base_load_p_set[load_name]
                        n_s.loads_t.p_set[load_name] = load_mult_series * base_p

                n_s.generators_t.p_max_pu["Wind"] = scenario["wind_cf"]
                n_s.generators_t.p_max_pu["Solar"] = scenario["solar_cf"]

                # Solve DC OPF
                status_s, cond_s = n_s.optimize(
                    snapshots=n_s.snapshots,
                    solver_name=SOLVER_NAME,
                    solver_options=SOLVER_OPTIONS,
                )

                sc_elapsed = time.perf_counter() - sc_start
                per_scenario_times.append(sc_elapsed)

                if str(status_s).lower() not in ("ok", "optimal"):
                    n_failed += 1
                    scenario_results.append(
                        {
                            "scenario": s_idx,
                            "status": str(status_s),
                            "condition": str(cond_s),
                            "solve_seconds": sc_elapsed,
                        }
                    )
                    continue

                # Collect results
                lmps = n_s.buses_t.marginal_price
                dispatch = n_s.generators_t.p
                total_cost = float(n_s.objective)

                lmp_mean = float(lmps.mean().mean()) if len(lmps) > 0 else None
                lmp_max = float(lmps.max().max()) if len(lmps) > 0 else None
                total_dispatch = float(dispatch.sum().sum()) if len(dispatch) > 0 else None

                scenario_results.append(
                    {
                        "scenario": s_idx,
                        "status": "ok",
                        "total_cost": total_cost,
                        "lmp_mean": lmp_mean,
                        "lmp_max": lmp_max,
                        "total_dispatch_mwh": total_dispatch,
                        "solve_seconds": sc_elapsed,
                        "wind_cf_mean": float(scenario["wind_cf"].mean()),
                        "load_mult_mean": float(scenario["load_mult"].mean()),
                    }
                )

            except Exception as sc_err:
                n_failed += 1
                scenario_results.append(
                    {
                        "scenario": s_idx,
                        "status": "error",
                        "error": f"{type(sc_err).__name__}: {sc_err}",
                        "solve_seconds": time.perf_counter() - sc_start,
                    }
                )

        # Aggregate timing
        n_succeeded = N_SCENARIOS - n_failed
        total_scenario_time = sum(r.get("solve_seconds", 0) for r in scenario_results)
        mean_scenario_time = total_scenario_time / N_SCENARIOS if N_SCENARIOS > 0 else 0.0

        print(f"=== Stochastic scenario wrap: {n_succeeded}/{N_SCENARIOS} succeeded ===")
        print(f"Mean scenario time: {mean_scenario_time:.3f}s")
        print(f"Total scenario time: {total_scenario_time:.3f}s")

        results["details"]["n_succeeded"] = n_succeeded
        results["details"]["n_failed"] = n_failed
        results["details"]["total_scenario_wall_clock_s"] = total_scenario_time
        results["details"]["mean_scenario_wall_clock_s"] = mean_scenario_time
        results["details"]["scenario_results"] = scenario_results

        # Cost statistics
        successful = [r for r in scenario_results if r.get("status") == "ok"]
        if successful:
            costs_list = [r["total_cost"] for r in successful]
            results["details"]["cost_stats"] = {
                "min": float(min(costs_list)),
                "max": float(max(costs_list)),
                "mean": float(np.mean(costs_list)),
                "std": float(np.std(costs_list)),
            }
            lmp_means = [r["lmp_mean"] for r in successful if r.get("lmp_mean") is not None]
            if lmp_means:
                results["details"]["lmp_mean_across_scenarios"] = float(np.mean(lmp_means))

        results["workarounds"].append(
            "Each scenario requires full network re-construction (re-load from .m file + re-add "
            "components). PyPSA has no built-in 'reset parameters for next scenario' API. "
            "Timeseries inputs via n.loads_t.p_set and n.generators_t.p_max_pu are clean; "
            "the overhead is in network rebuild per scenario."
        )

        if n_succeeded >= N_SCENARIOS * 0.9:
            results["status"] = "pass"
        else:
            results["errors"].append(f"Too many failed scenarios: {n_failed}/{N_SCENARIOS}")
            results["status"] = "fail"

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
