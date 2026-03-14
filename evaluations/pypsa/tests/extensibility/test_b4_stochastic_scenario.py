"""
Test B-4: Generate 20 scenarios, solve 12hr multi-period DCOPF for each on TINY

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Tool accepts timeseries inputs programmatically (not from config files only).
  Scenario loop is expressible without excessive per-scenario overhead. Results (prices,
  dispatch) are collectable in a structured format.
Tool: PyPSA 1.1.2
"""

import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
DEFAULT_TIMESERIES = str(REPO_ROOT / "data" / "timeseries" / "case39")

N_SCENARIOS = 20
N_HOURS = 12
RANDOM_SEED = 42

# Solver configuration (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,
}


def run(
    network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = DEFAULT_TIMESERIES
) -> dict:
    """Execute 20-scenario x 12-hour multi-period DCOPF.

    Uses Modified Tiny data for differentiated costs. Generates 20 load/renewable
    scenarios, solves each independently, collects LMPs and dispatch.

    Returns:
        dict with standard result keys.
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
        from matpower_loader import load_pypsa

        rng = np.random.default_rng(RANDOM_SEED)

        # 1. Load base network
        n_base = load_pypsa(network_file)

        # Set 12-hour snapshots
        snapshots = pd.date_range("2024-01-01", periods=N_HOURS, freq="h")
        n_base.set_snapshots(snapshots)

        # 2. Load Modified Tiny data for differentiated costs
        ts_dir = Path(timeseries_dir) if timeseries_dir else None
        if ts_dir and ts_dir.exists():
            # Load gen_temporal_params for differentiated costs
            gen_params_file = ts_dir / "gen_temporal_params.csv"
            if gen_params_file.exists():
                gen_params = pd.read_csv(gen_params_file)
                cost_map = {
                    "hydro": 5.0,
                    "nuclear": 10.0,
                    "coal_large": 25.0,
                    "gas_CC": 40.0,
                }
                gen_names = sorted(n_base.generators.index)
                for i, gen_name in enumerate(gen_names):
                    if i < len(gen_params):
                        tech = gen_params.iloc[i].get("tech_class_key", "gas_CC")
                        mc = cost_map.get(tech, 40.0)
                        n_base.generators.at[gen_name, "marginal_cost"] = mc
            else:
                # Fallback: assign linearly spaced costs
                gen_names = sorted(n_base.generators.index)
                costs = np.linspace(10, 100, len(gen_names))
                for gen_name, cost in zip(gen_names, costs):
                    n_base.generators.at[gen_name, "marginal_cost"] = float(cost)

            # Load 12-hour load profile from load_24h.csv
            load_file = ts_dir / "load_24h.csv"
            if load_file.exists():
                load_df = pd.read_csv(load_file, index_col=0)
                # load_df rows = bus IDs, columns = HR_1 ... HR_24
                # Use first 12 hours
                hr_cols = [f"HR_{h}" for h in range(1, N_HOURS + 1)]
                available_hrs = [c for c in hr_cols if c in load_df.columns]
                if available_hrs:
                    for load_name in n_base.loads.index:
                        bus_id = n_base.loads.at[load_name, "bus"]
                        # bus_id may be string like "16"
                        bus_key = str(int(float(bus_id))) if bus_id not in load_df.index else bus_id
                        if bus_key in load_df.index:
                            load_vals = load_df.loc[bus_key, available_hrs[:N_HOURS]].values.astype(
                                float
                            )
                            n_base.loads_t.p_set[load_name] = load_vals[:N_HOURS]
        else:
            # Fallback: assign differentiated costs without Modified Tiny
            gen_names = sorted(n_base.generators.index)
            costs = np.linspace(10, 100, len(gen_names))
            for gen_name, cost in zip(gen_names, costs):
                n_base.generators.at[gen_name, "marginal_cost"] = float(cost)

        # Store base load values for scenario scaling
        base_load_p_set = {}
        for load_name in n_base.loads.index:
            if load_name in n_base.loads_t.p_set.columns:
                base_load_p_set[load_name] = n_base.loads_t.p_set[load_name].values.copy()
            else:
                base_load_p_set[load_name] = np.full(N_HOURS, n_base.loads.at[load_name, "p_set"])

        results["details"]["n_buses"] = len(n_base.buses)
        results["details"]["n_generators"] = len(n_base.generators)
        results["details"]["n_scenarios"] = N_SCENARIOS
        results["details"]["n_hours"] = N_HOURS
        results["details"]["solver"] = SOLVER_NAME

        # 3. Generate 20 scenarios with varying load multipliers
        scenarios = []
        for s in range(N_SCENARIOS):
            load_mult = rng.uniform(0.85, 1.05, size=N_HOURS)
            scenarios.append({"load_mult": load_mult})

        # 4. Scenario loop — use n_base.copy() to avoid full reconstruction
        scenario_results = []
        per_scenario_times = []
        n_failed = 0

        for s_idx, scenario in enumerate(scenarios):
            sc_start = time.perf_counter()
            try:
                # Copy network (no file re-read, no model reconstruction)
                n_s = n_base.copy()

                # Apply scenario-specific load multipliers programmatically
                for load_name in n_s.loads.index:
                    base_p = base_load_p_set[load_name]
                    n_s.loads_t.p_set[load_name] = base_p * scenario["load_mult"]

                # Solve multi-period DCOPF
                status_s, cond_s = n_s.optimize(
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
                            "solve_seconds": sc_elapsed,
                        }
                    )
                    continue

                # Collect results (prices, dispatch) in structured format
                lmps = n_s.buses_t.marginal_price
                dispatch = n_s.generators_t.p
                total_cost = float(n_s.objective)

                lmp_mean = float(lmps.values.mean()) if lmps.size > 0 else None
                lmp_max = float(lmps.values.max()) if lmps.size > 0 else None
                lmp_min = float(lmps.values.min()) if lmps.size > 0 else None
                total_dispatch = float(dispatch.values.sum()) if dispatch.size > 0 else None

                scenario_results.append(
                    {
                        "scenario": s_idx,
                        "status": "ok",
                        "total_cost": round(total_cost, 2),
                        "lmp_mean": round(lmp_mean, 4) if lmp_mean is not None else None,
                        "lmp_max": round(lmp_max, 4) if lmp_max is not None else None,
                        "lmp_min": round(lmp_min, 4) if lmp_min is not None else None,
                        "total_dispatch_mwh": round(total_dispatch, 2)
                        if total_dispatch is not None
                        else None,
                        "solve_seconds": round(sc_elapsed, 4),
                        "load_mult_mean": round(float(scenario["load_mult"].mean()), 4),
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

        # 5. Aggregate results
        n_succeeded = N_SCENARIOS - n_failed
        total_scenario_time = sum(r.get("solve_seconds", 0) for r in scenario_results)
        mean_scenario_time = total_scenario_time / N_SCENARIOS if N_SCENARIOS > 0 else 0.0

        results["details"]["n_succeeded"] = n_succeeded
        results["details"]["n_failed"] = n_failed
        results["details"]["total_scenario_wall_clock_s"] = round(total_scenario_time, 4)
        results["details"]["mean_scenario_wall_clock_s"] = round(mean_scenario_time, 4)

        # Cost and LMP statistics across successful scenarios
        successful = [r for r in scenario_results if r.get("status") == "ok"]
        if successful:
            costs_list = [r["total_cost"] for r in successful]
            results["details"]["cost_stats"] = {
                "min": round(min(costs_list), 2),
                "max": round(max(costs_list), 2),
                "mean": round(float(np.mean(costs_list)), 2),
                "std": round(float(np.std(costs_list)), 2),
            }
            lmp_means = [r["lmp_mean"] for r in successful if r.get("lmp_mean") is not None]
            if lmp_means:
                results["details"]["lmp_mean_across_scenarios"] = round(
                    float(np.mean(lmp_means)), 4
                )

        # Include representative scenario results (first 5 + worst cost)
        results["details"]["scenario_sample"] = scenario_results[:5]
        if successful:
            worst_cost = max(successful, key=lambda r: r["total_cost"])
            best_cost = min(successful, key=lambda r: r["total_cost"])
            results["details"]["worst_cost_scenario"] = worst_cost
            results["details"]["best_cost_scenario"] = best_cost

        print(f"=== Stochastic scenario sweep: {n_succeeded}/{N_SCENARIOS} succeeded ===")
        print(f"Mean scenario time: {mean_scenario_time:.3f}s")
        print(f"Total scenario time: {total_scenario_time:.3f}s")
        if successful:
            print(f"Cost range: [{min(costs_list):.2f}, {max(costs_list):.2f}]")
            print(f"LMP mean across scenarios: {np.mean(lmp_means):.4f}")

        # 6. Pass condition assessment
        # - Timeseries inputs accepted programmatically: YES (loads_t.p_set DataFrame)
        # - Scenario loop without excessive overhead: YES (n.copy() avoids file re-read)
        # - Results collectable in structured format: YES (LMPs, dispatch, costs collected)
        if n_succeeded >= N_SCENARIOS * 0.9:
            results["status"] = "pass"
        else:
            results["errors"].append(f"Too many failed scenarios: {n_failed}/{N_SCENARIOS}")

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
