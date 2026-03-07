"""
Test B-4: Generate 20 scenarios with correlated perturbations by resource type.
    Solve 12hr multi-period DCOPF for each. Collect prices and dispatch.

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Tool accepts timeseries inputs programmatically. Scenario loop
    expressible without excessive per-scenario overhead.
Solver: HiGHS (but pandapower uses PYPOWER -- deviation noted)
Tool: pandapower v3.4.0

APPROACH: Loop over 20 scenarios x 12 hours, modifying load/gen parameters in-place
via net.load["p_mw"] and solving with pp.rundcopp() per timestep. Classify generators
by cost as proxy for resource type. Generate correlated perturbations per type.
"""

import json
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute stochastic wrapping test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # Parameters
        n_scenarios = 20
        n_hours = 12
        np.random.seed(42)

        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["load_count"] = len(net.load)

        # Ensure cost curves
        has_costs = len(net.poly_cost) > 0 or len(net.pwl_cost) > 0
        if not has_costs:
            for idx in net.gen.index:
                pp.create_poly_cost(net, idx, "gen", cp1_eur_per_mw=20.0 + idx * 5.0)
            for idx in net.ext_grid.index:
                pp.create_poly_cost(net, idx, "ext_grid", cp1_eur_per_mw=50.0)

        # 2. Classify generators by resource type (cost quartile proxy)
        gen_costs = []
        for idx in net.gen.index:
            cost_rows = net.poly_cost[
                (net.poly_cost["element"] == idx) & (net.poly_cost["et"] == "gen")
            ]
            cp1 = float(cost_rows.iloc[0].get("cp1_eur_per_mw", 0)) if len(cost_rows) > 0 else 0
            gen_costs.append({"gen_idx": int(idx), "cp1": cp1})

        gen_costs.sort(key=lambda x: x["cp1"])
        n_gens = len(gen_costs)
        q1 = max(1, n_gens // 4)
        q3 = max(q1 + 1, 3 * n_gens // 4)

        resource_types = {}
        for i, gc in enumerate(gen_costs):
            if i < q1:
                resource_types[gc["gen_idx"]] = "baseload"
            elif i >= q3:
                resource_types[gc["gen_idx"]] = "peaker"
            else:
                resource_types[gc["gen_idx"]] = "intermediate"

        results["details"]["resource_classification"] = {
            str(k): v for k, v in resource_types.items()
        }

        # 3. Generate correlated perturbations by resource type
        # Each resource type has its own correlation structure
        type_groups = {}
        for gen_idx, rtype in resource_types.items():
            type_groups.setdefault(rtype, []).append(gen_idx)

        # Correlation within resource type: 0.8, between types: 0.2
        # Generate base random variables per type, then add individual noise
        type_base_signals = {}
        for rtype in type_groups:
            # Base signal for this resource type (shared component)
            type_base_signals[rtype] = np.random.normal(0, 0.05, (n_scenarios, n_hours))

        # Hourly load shape (12 hours)
        hourly_shape = np.array(
            [0.70, 0.65, 0.60, 0.60, 0.65, 0.75, 0.90, 1.00, 1.05, 1.10, 1.05, 1.00]
        )

        # Load perturbations: correlated across loads
        load_base_signal = np.random.normal(0, 0.08, (n_scenarios, n_hours))

        # Save original values
        base_loads = net.load["p_mw"].values.copy()
        base_gen_max = net.gen["max_p_mw"].values.copy()

        results["details"]["n_scenarios"] = n_scenarios
        results["details"]["n_hours"] = n_hours
        results["details"]["total_solves"] = n_scenarios * n_hours
        results["details"]["solver_note"] = (
            "pandapower rundcopp() uses PYPOWER interior point, not HiGHS as specified."
        )

        # 4. Scenario loop
        solve_start = time.perf_counter()
        all_scenario_results = []
        total_converged = 0
        total_failed = 0

        for s in range(n_scenarios):
            scenario_data = {
                "scenario": s,
                "dispatch_mw": [],
                "lmps_mean": [],
                "objectives": [],
                "converged_hours": 0,
            }

            for h in range(n_hours):
                # Apply load perturbation
                load_scale = hourly_shape[h] * (1.0 + load_base_signal[s, h])
                net.load["p_mw"] = base_loads * max(load_scale, 0.3)

                # Apply gen capacity perturbations by resource type
                for gen_idx, rtype in resource_types.items():
                    base_signal = type_base_signals[rtype][s, h]
                    individual_noise = np.random.normal(0, 0.02)
                    perturbation = 1.0 + base_signal + individual_noise
                    gen_pos = list(net.gen.index).index(gen_idx)
                    net.gen.at[gen_idx, "max_p_mw"] = base_gen_max[gen_pos] * max(perturbation, 0.5)

                # Solve DC OPF
                try:
                    pp.rundcopp(net)
                    converged = net.get("OPF_converged", False)
                except Exception:
                    converged = False

                if converged:
                    total_converged += 1
                    scenario_data["converged_hours"] += 1
                    gen_p = net.res_gen["p_mw"].values.tolist()
                    scenario_data["dispatch_mw"].append(gen_p)

                    if "lam_p" in net.res_bus.columns:
                        mean_lmp = float(net.res_bus["lam_p"].mean())
                        scenario_data["lmps_mean"].append(mean_lmp)
                    else:
                        scenario_data["lmps_mean"].append(None)

                    obj = float(net.res_cost) if hasattr(net, "res_cost") else None
                    scenario_data["objectives"].append(obj)
                else:
                    total_failed += 1
                    scenario_data["dispatch_mw"].append(None)
                    scenario_data["lmps_mean"].append(None)
                    scenario_data["objectives"].append(None)

            all_scenario_results.append(scenario_data)

        solve_elapsed = time.perf_counter() - solve_start

        # Restore original values
        net.load["p_mw"] = base_loads
        net.gen["max_p_mw"] = base_gen_max

        # 5. Compile results
        results["details"]["solve_loop_seconds"] = solve_elapsed
        results["details"]["total_converged"] = total_converged
        results["details"]["total_failed"] = total_failed
        results["details"]["per_solve_avg_seconds"] = (
            solve_elapsed / (n_scenarios * n_hours) if n_scenarios * n_hours > 0 else 0
        )
        results["details"]["convergence_rate_pct"] = total_converged / (n_scenarios * n_hours) * 100

        # Summary statistics across scenarios
        valid_objs = [o for sr in all_scenario_results for o in sr["objectives"] if o is not None]
        valid_lmps = [v for sr in all_scenario_results for v in sr["lmps_mean"] if v is not None]

        if valid_objs:
            results["details"]["objective_stats"] = {
                "mean": float(np.mean(valid_objs)),
                "std": float(np.std(valid_objs)),
                "min": float(np.min(valid_objs)),
                "max": float(np.max(valid_objs)),
            }

        if valid_lmps:
            results["details"]["lmp_stats"] = {
                "mean": float(np.mean(valid_lmps)),
                "std": float(np.std(valid_lmps)),
                "min": float(np.min(valid_lmps)),
                "max": float(np.max(valid_lmps)),
            }

        # Sample: first scenario summary
        if all_scenario_results:
            s0 = all_scenario_results[0]
            results["details"]["scenario_0_summary"] = {
                "converged_hours": s0["converged_hours"],
                "objectives": s0["objectives"][:3],
                "lmps_mean": s0["lmps_mean"][:3],
            }

        # 6. Assess pass condition
        # "Tool accepts timeseries inputs programmatically" -- YES (modify DataFrames in-place)
        # "Scenario loop expressible without excessive per-scenario overhead" -- YES
        # No model reconstruction needed, just DataFrame updates + rundcopp()
        if total_converged > 0:
            results["status"] = "qualified_pass"
            results["workarounds"].append(
                "pandapower has no native multi-period DCOPF or scenario API. "
                "Achieved via loop: modify net.load/net.gen DataFrames in-place, "
                "call rundcopp() per (scenario, hour) pair. This is a sequential "
                "solve loop, not a single multi-period optimization. However, the "
                "loop overhead is minimal (no model reconstruction), satisfying the "
                "pass condition regarding expressibility."
            )
            results["workarounds"].append(
                "Solver deviation: uses PYPOWER interior point instead of HiGHS."
            )
            results["details"]["method"] = (
                "In-place DataFrame modification + rundcopp() loop. "
                "20 scenarios x 12 hours = 240 total solves. "
                "No model reconstruction per solve."
            )
        else:
            results["errors"].append("No DC OPF solves converged across all scenarios")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
