"""
Probe 006: Verify 2.1% convergence rate claim for stochastic DCOPF on ACTIVSg2000.

Claim: "Stochastic DCOPF wrapping qualified_pass despite 2.1% solver convergence rate
(5 of 240 solves)" in C-6.

Approach:
1. Load ACTIVSg2000 via from_mpc
2. Solve base-case DC OPF (no perturbations) — does it converge?
3. Apply small load perturbations (same approach as original test) for a subset of scenarios
4. Report convergence rate and compare to 2.1%
"""

import json
import time

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc

start = time.perf_counter()
results = {}

try:
    # 1. Load network
    net = from_mpc("/workspace/data/networks/case_ACTIVSg2000.m", f_hz=60)
    results["bus_count"] = len(net.bus)
    results["gen_count"] = len(net.gen)
    results["load_count"] = len(net.load)

    # Ensure cost curves exist
    has_costs = len(net.poly_cost) > 0 or len(net.pwl_cost) > 0
    results["has_imported_costs"] = has_costs
    if not has_costs:
        for idx in net.gen.index:
            pp.create_poly_cost(net, idx, "gen", cp1_eur_per_mw=20.0 + idx * 0.5)
        for idx in net.ext_grid.index:
            pp.create_poly_cost(net, idx, "ext_grid", cp1_eur_per_mw=50.0)

    # 2. Base case DC OPF — no perturbations
    try:
        pp.rundcopp(net)
        base_converged = net.get("OPF_converged", False)
    except Exception as e:
        base_converged = False
        results["base_case_error"] = str(e)
    results["base_case_converged"] = base_converged
    if base_converged:
        results["base_case_objective"] = float(net.res_cost)

    # 3. Replicate the original test scenario loop (smaller subset for speed)
    # Use same RNG seed and perturbation approach as original
    np.random.seed(42)
    n_scenarios = 20
    n_hours = 12

    hourly_shape = np.array(
        [0.70, 0.65, 0.60, 0.60, 0.65, 0.75, 0.90, 1.00, 1.05, 1.10, 1.05, 1.00]
    )
    load_base_signal = np.random.normal(0, 0.08, (n_scenarios, n_hours))

    # Classify generators (same as original)
    gen_costs = []
    for idx in net.gen.index:
        cost_rows = net.poly_cost[
            (net.poly_cost["element"] == idx) & (net.poly_cost["et"] == "gen")
        ]
        cp1 = (
            float(cost_rows.iloc[0].get("cp1_eur_per_mw", 0))
            if len(cost_rows) > 0
            else 0
        )
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

    type_groups = {}
    for gen_idx, rtype in resource_types.items():
        type_groups.setdefault(rtype, []).append(gen_idx)

    type_base_signals = {}
    for rtype in type_groups:
        type_base_signals[rtype] = np.random.normal(0, 0.05, (n_scenarios, n_hours))

    base_loads = net.load["p_mw"].values.copy()
    base_gen_max = net.gen["max_p_mw"].values.copy()

    # Run all 240 solves (same as original)
    total_converged = 0
    total_failed = 0
    all_objectives = []
    convergence_by_hour = {h: {"converged": 0, "failed": 0} for h in range(n_hours)}

    solve_start = time.perf_counter()
    for s in range(n_scenarios):
        for h in range(n_hours):
            load_scale = hourly_shape[h] * (1.0 + load_base_signal[s, h])
            net.load["p_mw"] = base_loads * max(load_scale, 0.3)

            for gen_idx, rtype in resource_types.items():
                base_signal = type_base_signals[rtype][s, h]
                individual_noise = np.random.normal(0, 0.02)
                perturbation = 1.0 + base_signal + individual_noise
                gen_pos = list(net.gen.index).index(gen_idx)
                net.gen.at[gen_idx, "max_p_mw"] = base_gen_max[gen_pos] * max(
                    perturbation, 0.5
                )

            try:
                pp.rundcopp(net)
                converged = net.get("OPF_converged", False)
            except Exception:
                converged = False

            if converged:
                total_converged += 1
                convergence_by_hour[h]["converged"] += 1
                obj = float(net.res_cost) if hasattr(net, "res_cost") else None
                if obj is not None:
                    all_objectives.append(obj)
            else:
                total_failed += 1
                convergence_by_hour[h]["failed"] += 1

    solve_elapsed = time.perf_counter() - solve_start

    # Restore
    net.load["p_mw"] = base_loads
    net.gen["max_p_mw"] = base_gen_max

    total_solves = n_scenarios * n_hours
    results["total_solves"] = total_solves
    results["total_converged"] = total_converged
    results["total_failed"] = total_failed
    results["convergence_rate_pct"] = round(total_converged / total_solves * 100, 2)
    results["solve_loop_seconds"] = round(solve_elapsed, 2)
    results["per_solve_avg_seconds"] = round(solve_elapsed / total_solves, 3)

    if all_objectives:
        results["objective_mean"] = round(float(np.mean(all_objectives)), 2)

    # Also test: what about solving with no perturbation at different load levels?
    results["convergence_by_hour"] = {
        str(h): convergence_by_hour[h] for h in range(n_hours)
    }

    # 4. Diagnostic: test uniform load scaling without gen perturbation
    uniform_results = []
    for scale in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1]:
        net.load["p_mw"] = base_loads * scale
        net.gen["max_p_mw"] = base_gen_max  # no gen perturbation
        try:
            pp.rundcopp(net)
            conv = net.get("OPF_converged", False)
        except Exception:
            conv = False
        uniform_results.append({"scale": scale, "converged": conv})
    results["uniform_load_scale_convergence"] = uniform_results

    net.load["p_mw"] = base_loads
    net.gen["max_p_mw"] = base_gen_max

except Exception as e:
    results["error"] = f"{type(e).__name__}: {e}"
    import traceback

    results["traceback"] = traceback.format_exc()

results["wall_clock_seconds"] = round(time.perf_counter() - start, 2)
print(json.dumps(results, indent=2, default=str))
