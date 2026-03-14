"""
Test B-4: 20-scenario 12hr multi-period DCOPF with stochastic timeseries

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Tool accepts timeseries inputs programmatically (not from config
    files only). Scenario loop is expressible without excessive per-scenario
    overhead. Results (prices, dispatch) are collectable in a structured format.
Tool: pandapower 3.4.0

Note: pandapower's rundcopp() is single-period. Each "period" must be an
independent solve. The test is about scenario wrapping, not multi-period
optimization.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

# Differentiated cost curves
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}

BRANCH_DERATING = 0.70
N_SCENARIOS = 20
N_HOURS = 12  # first 12 hours


def _setup_dcopf(net, timeseries_dir: str) -> None:
    """Set up the network for DC OPF with differentiated costs."""
    import pandapower as pp

    ts_dir = Path(timeseries_dir)
    gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

    for idx in net.gen.index:
        net.gen.at[idx, "controllable"] = True
        net.gen.at[idx, "min_p_mw"] = 0.0
    for idx in net.ext_grid.index:
        net.ext_grid.at[idx, "controllable"] = True
        net.ext_grid.at[idx, "min_p_mw"] = -9999.0
        net.ext_grid.at[idx, "max_p_mw"] = 9999.0

    net.bus["min_vm_pu"] = 0.9
    net.bus["max_vm_pu"] = 1.1

    net.poly_cost.drop(net.poly_cost.index, inplace=True)
    if hasattr(net, "pwl_cost"):
        net.pwl_cost.drop(net.pwl_cost.index, inplace=True)

    for _, row in gen_params.iterrows():
        tech = row["tech_class_key"]
        costs = COST_BY_TECH.get(tech, COST_BY_TECH["gas_CC"])
        bus_id_pp = int(row["bus_id"]) - 1
        ext_match = net.ext_grid[net.ext_grid["bus"] == bus_id_pp]
        gen_match = net.gen[net.gen["bus"] == bus_id_pp]
        if len(ext_match) > 0:
            pp.create_poly_cost(
                net,
                element=ext_match.index[0],
                et="ext_grid",
                cp1_eur_per_mw=costs["cp1"],
                cp2_eur_per_mw2=costs["cp2"],
                cp0_eur=0.0,
            )
        elif len(gen_match) > 0:
            pp.create_poly_cost(
                net,
                element=gen_match.index[0],
                et="gen",
                cp1_eur_per_mw=costs["cp1"],
                cp2_eur_per_mw2=costs["cp2"],
                cp0_eur=0.0,
            )

    net.line["max_loading_percent"] = 100.0
    net.line["max_i_ka"] = net.line["max_i_ka"] * BRANCH_DERATING
    if len(net.trafo) > 0:
        net.trafo["max_loading_percent"] = 100.0


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute 20-scenario 12-hour stochastic DCOPF wrapping test."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandapower as pp

        if timeseries_dir is None:
            results["errors"].append("timeseries_dir is required for B-4")
            return results

        ts_dir = Path(timeseries_dir)

        # Load base load profile (24h) and scenario multipliers
        load_24h = pd.read_csv(ts_dir / "load_24h.csv")
        scenario_mults = pd.read_csv(ts_dir / "scenarios" / "scenario_multipliers_50x24.csv")
        renewable_units = pd.read_csv(ts_dir / "renewable_units.csv")
        wind_forecast = pd.read_csv(ts_dir / "wind_forecast_24h.csv")
        solar_forecast = pd.read_csv(ts_dir / "solar_forecast_24h.csv")

        results["details"]["load_profile_shape"] = list(load_24h.shape)
        results["details"]["scenario_multipliers_shape"] = list(scenario_mults.shape)
        results["details"]["n_scenarios_requested"] = N_SCENARIOS
        results["details"]["n_hours"] = N_HOURS

        # Build base network once
        net_template = load_pandapower(network_file)
        _setup_dcopf(net_template, timeseries_dir)

        hour_cols = [f"HR_{h}" for h in range(1, N_HOURS + 1)]

        # Add renewable generators as sgen elements to the template
        # Wind generators
        wind_sgen_indices = {}
        for _, row in renewable_units.iterrows():
            bus_pp = int(row["bus_id"]) - 1
            sgen_idx = pp.create_sgen(
                net_template,
                bus=bus_pp,
                p_mw=0.0,
                name=row["gen_uid"],
                controllable=False,
            )
            wind_sgen_indices[row["gen_uid"]] = sgen_idx

        results["details"]["renewable_sgen_count"] = len(wind_sgen_indices)

        # Collect results across all scenarios and hours
        all_dispatch = []  # List of dicts: {scenario, hour, gen_dispatch, objective, ...}
        all_lmps = []

        n_solves = 0
        n_converged = 0

        solve_start = time.perf_counter()

        for scen_idx in range(1, N_SCENARIOS + 1):
            scenario_dispatch = []
            scenario_lmps = []

            for hour_idx, hour_col in enumerate(hour_cols):
                hour_num = hour_idx + 1

                # 1. Update loads for this hour
                for load_idx in net_template.load.index:
                    load_bus = net_template.load.at[load_idx, "bus"]
                    matpower_bus = load_bus + 1  # convert to 1-indexed
                    match = load_24h[load_24h["bus_id"] == matpower_bus]
                    if len(match) > 0:
                        net_template.load.at[load_idx, "p_mw"] = float(match[hour_col].iloc[0])

                # 2. Update renewable generation with scenario multipliers
                scen_rows = scenario_mults[scenario_mults["scenario"] == scen_idx]
                for gen_uid, sgen_idx in wind_sgen_indices.items():
                    gen_row = scen_rows[scen_rows["gen_uid"] == gen_uid]
                    if len(gen_row) > 0:
                        mult = float(gen_row[hour_col].iloc[0])
                    else:
                        mult = 1.0

                    # Get forecast value
                    ren_type = renewable_units[renewable_units["gen_uid"] == gen_uid]["type"].iloc[
                        0
                    ]
                    if ren_type == "wind":
                        forecast_df = wind_forecast
                    else:
                        forecast_df = solar_forecast

                    forecast_row = forecast_df[forecast_df["gen_uid"] == gen_uid]
                    if len(forecast_row) > 0:
                        base_gen = float(forecast_row[hour_col].iloc[0])
                    else:
                        base_gen = 0.0

                    net_template.sgen.at[sgen_idx, "p_mw"] = base_gen * mult

                # 3. Solve DC OPF
                try:
                    pp.rundcopp(net_template)
                    n_solves += 1

                    if net_template.OPF_converged:
                        n_converged += 1

                        # Collect dispatch
                        gen_p = net_template.res_gen["p_mw"].to_dict()
                        ext_p = net_template.res_ext_grid["p_mw"].to_dict()
                        obj = float(net_template.res_cost)

                        dispatch_record = {
                            "scenario": scen_idx,
                            "hour": hour_num,
                            "gen_dispatch_mw": gen_p,
                            "ext_grid_dispatch_mw": ext_p,
                            "objective": obj,
                            "total_gen_mw": float(
                                net_template.res_gen["p_mw"].sum()
                                + net_template.res_ext_grid["p_mw"].sum()
                            ),
                        }
                        scenario_dispatch.append(dispatch_record)

                        # Extract LMPs from internal _ppc
                        ppc = net_template._ppc
                        if ppc is not None and "bus" in ppc and ppc["bus"].shape[1] > 13:
                            lam_p = ppc["bus"][:, 13].tolist()
                            scenario_lmps.append(
                                {
                                    "scenario": scen_idx,
                                    "hour": hour_num,
                                    "lam_p": lam_p,
                                }
                            )
                    else:
                        n_solves += 0  # already counted
                        scenario_dispatch.append(
                            {
                                "scenario": scen_idx,
                                "hour": hour_num,
                                "converged": False,
                            }
                        )
                except Exception as e:
                    n_solves += 1
                    scenario_dispatch.append(
                        {
                            "scenario": scen_idx,
                            "hour": hour_num,
                            "error": str(e),
                        }
                    )

            all_dispatch.extend(scenario_dispatch)
            all_lmps.extend(scenario_lmps)

        solve_time = time.perf_counter() - solve_start
        total_solves = N_SCENARIOS * N_HOURS

        results["details"]["total_solves"] = total_solves
        results["details"]["n_solves_attempted"] = n_solves
        results["details"]["n_converged"] = n_converged
        results["details"]["solve_time_seconds"] = solve_time
        results["details"]["time_per_solve_ms"] = (
            solve_time / total_solves * 1000 if total_solves > 0 else 0
        )

        # Summarize results in structured format
        converged_dispatch = [d for d in all_dispatch if "objective" in d]
        if converged_dispatch:
            objectives = [d["objective"] for d in converged_dispatch]
            total_gens = [d["total_gen_mw"] for d in converged_dispatch]
            results["details"]["objective_stats"] = {
                "min": float(np.min(objectives)),
                "max": float(np.max(objectives)),
                "mean": float(np.mean(objectives)),
                "std": float(np.std(objectives)),
            }
            results["details"]["total_gen_stats_mw"] = {
                "min": float(np.min(total_gens)),
                "max": float(np.max(total_gens)),
                "mean": float(np.mean(total_gens)),
            }

        # Show dispatch variation across scenarios for hour 1
        hour1_dispatch = [d for d in converged_dispatch if d["hour"] == 1]
        if hour1_dispatch:
            h1_obj = [d["objective"] for d in hour1_dispatch]
            results["details"]["hour1_objective_range"] = {
                "min": float(np.min(h1_obj)),
                "max": float(np.max(h1_obj)),
                "spread_pct": float((np.max(h1_obj) - np.min(h1_obj)) / np.mean(h1_obj) * 100),
            }

        results["details"]["lmp_records_collected"] = len(all_lmps)
        results["details"]["dispatch_records_collected"] = len(converged_dispatch)

        # Sample: first scenario, first 3 hours
        results["details"]["sample_dispatch"] = converged_dispatch[:3] if converged_dispatch else []

        # Check pass conditions
        timeseries_programmatic = True  # loads set via DataFrame assignment
        scenario_loop_clean = True  # simple for loop, no per-scenario model rebuild
        results_structured = len(converged_dispatch) > 0 and len(all_lmps) > 0

        results["details"]["timeseries_programmatic"] = timeseries_programmatic
        results["details"]["scenario_loop_clean"] = scenario_loop_clean
        results["details"]["results_structured"] = results_structured

        convergence_rate = n_converged / total_solves if total_solves > 0 else 0
        results["details"]["convergence_rate"] = convergence_rate

        if timeseries_programmatic and scenario_loop_clean and results_structured:
            if convergence_rate >= 0.95:
                results["status"] = "pass"
            else:
                results["status"] = "qualified_pass"
                results["workarounds"].append(
                    f"Only {convergence_rate:.1%} of solves converged "
                    f"({n_converged}/{total_solves})"
                )
        else:
            if not results_structured:
                results["errors"].append("Could not collect structured results")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
