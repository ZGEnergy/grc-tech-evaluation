"""
Test A-8: Solve multi-period (12hr, hourly) DCOPF with stochastic load and
    renewable generation scenarios. Independent perturbations by resource type.

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Tool natively supports scenario-indexed timeseries for load, wind, and
    solar - the stochastic structure is part of the optimization formulation (e.g.,
    scenario tree, two-stage stochastic program), not just independent deterministic
    solves in a loop. Perturbations are independent by resource type. Prices extractable
    from solution.
Tool: pandapower v3.4.0

CRITICAL NOTE: pandapower does NOT support scenario-indexed stochastic OPF. The pass
    condition explicitly requires native stochastic formulation, NOT loop-based
    sequential solves. This test FAILS by design. The script demonstrates what IS
    achievable (sequential multi-period DCOPF via loop) and documents the limitation.
"""

import json
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute stochastic timeseries test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    try:
        # Parameters
        n_hours = 12
        n_scenarios = 5  # Small number for demonstration
        np.random.seed(42)

        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["load_count"] = len(net.load)

        # Check for cost curves
        has_costs = len(net.poly_cost) > 0 or len(net.pwl_cost) > 0
        if not has_costs:
            for idx in net.gen.index:
                pp.create_poly_cost(net, idx, "gen", cp1_eur_per_mw=20.0 + idx * 5.0)
            for idx in net.ext_grid.index:
                pp.create_poly_cost(net, idx, "ext_grid", cp1_eur_per_mw=50.0)
            results["details"]["cost_setup"] = "Added linear costs (not from import)"
        else:
            results["details"]["cost_setup"] = "Cost curves from MATPOWER import"

        # 2. Document the fundamental limitation
        results["details"]["native_stochastic_support"] = False
        results["details"]["limitation"] = (
            "pandapower has NO native scenario-indexed stochastic OPF formulation. "
            "It provides run_timeseries() for sequential deterministic solves over time, "
            "but this is NOT a stochastic program - each timestep is solved independently "
            "with no scenario tree, no recourse decisions, no expectation-based objective. "
            "The pass condition requires the stochastic structure to be part of the "
            "optimization formulation, which pandapower cannot provide."
        )

        # 3. Demonstrate what IS achievable: sequential multi-period DCOPF
        # Classify generators by cost (proxy for resource type)
        gen_costs = []
        for idx in net.gen.index:
            cost_rows = net.poly_cost[
                (net.poly_cost["element"] == idx) & (net.poly_cost["et"] == "gen")
            ]
            if len(cost_rows) > 0:
                cp1 = float(cost_rows.iloc[0].get("cp1_eur_per_mw", 0))
            else:
                cp1 = 0.0
            gen_costs.append({"gen_idx": int(idx), "cp1": cp1})

        gen_costs.sort(key=lambda x: x["cp1"])
        n_gens = len(gen_costs)
        q1 = n_gens // 4
        q3 = 3 * n_gens // 4

        resource_types = {}
        for i, gc in enumerate(gen_costs):
            if i < q1:
                resource_types[gc["gen_idx"]] = "baseload"
            elif i >= q3:
                resource_types[gc["gen_idx"]] = "peaker"
            else:
                resource_types[gc["gen_idx"]] = "intermediate"

        results["details"]["resource_classification"] = resource_types

        # Generate load profiles with hourly variation
        base_loads = net.load["p_mw"].values.copy()
        hourly_shape = np.array(
            [0.7, 0.65, 0.6, 0.6, 0.65, 0.75, 0.9, 1.0, 1.05, 1.1, 1.05, 1.0]
        )  # 12 hours

        # Generate independent perturbations per resource type per scenario
        load_perturbations = np.random.normal(1.0, 0.1, (n_scenarios, n_hours))

        # Sequential solve loop (this is NOT stochastic OPF, just sequential DCOPF)
        start = time.perf_counter()
        all_results = []

        for s in range(n_scenarios):
            scenario_results = {"scenario": s, "hours": []}
            for h in range(n_hours):
                # Apply load perturbation
                scale = hourly_shape[h] * load_perturbations[s, h]
                net.load["p_mw"] = base_loads * scale

                # Solve DCOPF
                try:
                    pp.rundcopp(net)
                    converged = net.get("OPF_converged", False)
                    if converged:
                        lmps = (
                            net.res_bus["lam_p"].values.tolist()
                            if "lam_p" in net.res_bus.columns
                            else []
                        )
                        gen_p = net.res_gen["p_mw"].values.tolist()
                        obj = float(net.res_cost) if hasattr(net, "res_cost") else None
                    else:
                        lmps = []
                        gen_p = []
                        obj = None
                except Exception:
                    converged = False
                    lmps = []
                    gen_p = []
                    obj = None

                scenario_results["hours"].append(
                    {
                        "hour": h,
                        "converged": converged,
                        "objective": obj,
                        "mean_lmp": float(np.mean(lmps)) if lmps else None,
                        "total_gen_mw": float(np.sum(gen_p)) if gen_p else None,
                    }
                )
            all_results.append(scenario_results)

        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed

        # Restore original loads
        net.load["p_mw"] = base_loads

        # 4. Summarize what was achieved
        total_solves = n_scenarios * n_hours
        converged_count = sum(1 for sr in all_results for hr in sr["hours"] if hr["converged"])
        results["details"]["total_solves"] = total_solves
        results["details"]["converged_solves"] = converged_count
        results["details"]["n_scenarios"] = n_scenarios
        results["details"]["n_hours"] = n_hours
        results["details"]["per_solve_avg_seconds"] = (
            elapsed / total_solves if total_solves > 0 else 0
        )

        # Sample results from first scenario
        if all_results:
            results["details"]["scenario_0_sample"] = all_results[0]["hours"][:3]

        # 5. FAIL: does not meet pass condition
        results["status"] = "fail"
        results["errors"].append(
            "pandapower does not support native scenario-indexed stochastic OPF. "
            "The sequential loop-based approach demonstrated here does NOT satisfy "
            "the pass condition, which requires the stochastic structure to be part "
            "of the optimization formulation (scenario tree, two-stage program, etc.)."
        )
        results["details"]["what_was_demonstrated"] = (
            "Sequential multi-period DCOPF via loop: each (scenario, hour) pair "
            "solved independently with pandapower.rundcopp(). Load perturbations "
            "applied per timestep. This is deterministic looping, NOT stochastic "
            "optimization."
        )
        results["details"]["output_format"] = "pandas.DataFrame (per-solve)"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
