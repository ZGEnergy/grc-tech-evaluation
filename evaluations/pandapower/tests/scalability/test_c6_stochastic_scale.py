"""
Test C-6: 20-scenario stochastic DCOPF at scale (B-4 workaround approach)

Dimension: scalability
Network: SMALL (ACTIVSg2000, ~2000 buses)
Pass condition: N/A - A-8 (native stochastic OPF) FAILED. This tests the B-4
    loop-based workaround at scale. Status reflects that this is testing the
    workaround, not native capability.
Tool: pandapower v3.4.0

APPROACH: 20 scenarios x 12 hours loop-based sequential DCOPF, modifying
load/gen DataFrames in-place per (scenario, hour) pair.
"""

import json
import os
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg2000.m") -> dict:
    """Execute stochastic DCOPF at scale and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        n_scenarios = 20
        n_hours = 12
        np.random.seed(42)

        # 1. Load network
        load_start = time.perf_counter()
        net = from_mpc(network_file, f_hz=60)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["load_count"] = len(net.load)
        results["details"]["ext_grid_count"] = len(net.ext_grid)

        # Ensure cost curves
        has_costs = len(net.poly_cost) > 0 or len(net.pwl_cost) > 0
        if not has_costs:
            for idx in net.gen.index:
                pp.create_poly_cost(net, idx, "gen", cp1_eur_per_mw=20.0 + idx * 0.5)
            for idx in net.ext_grid.index:
                pp.create_poly_cost(net, idx, "ext_grid", cp1_eur_per_mw=50.0)
            results["details"]["cost_setup"] = "Added linear costs"
        else:
            results["details"]["cost_setup"] = "Imported from MATPOWER case"

        # 2. Classify generators by cost quartile
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

        # 3. Generate correlated perturbations
        type_groups = {}
        for gen_idx, rtype in resource_types.items():
            type_groups.setdefault(rtype, []).append(gen_idx)

        type_base_signals = {}
        for rtype in type_groups:
            type_base_signals[rtype] = np.random.normal(0, 0.05, (n_scenarios, n_hours))

        hourly_shape = np.array(
            [0.70, 0.65, 0.60, 0.60, 0.65, 0.75, 0.90, 1.00, 1.05, 1.10, 1.05, 1.00]
        )
        load_base_signal = np.random.normal(0, 0.08, (n_scenarios, n_hours))

        # Save originals
        base_loads = net.load["p_mw"].values.copy()
        base_gen_max = net.gen["max_p_mw"].values.copy()

        results["details"]["n_scenarios"] = n_scenarios
        results["details"]["n_hours"] = n_hours
        results["details"]["total_solves"] = n_scenarios * n_hours
        results["details"]["solver_note"] = (
            "PYPOWER interior point (only option for pandapower DC OPF)"
        )
        results["details"]["approach_note"] = (
            "A-8 (native stochastic OPF) FAILED. This tests the B-4 loop-based "
            "workaround at scale: modify DataFrames in-place per (scenario, hour), "
            "call rundcopp() sequentially."
        )

        # Memory before
        try:
            import resource

            mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # noqa: F841
        except Exception:
            mem_before = None  # noqa: F841

        # 4. Scenario loop
        solve_start = time.perf_counter()
        total_converged = 0
        total_failed = 0
        all_objectives = []
        all_lmps = []

        for s in range(n_scenarios):
            for h in range(n_hours):
                # Apply load perturbation
                load_scale = hourly_shape[h] * (1.0 + load_base_signal[s, h])
                net.load["p_mw"] = base_loads * max(load_scale, 0.3)

                # Apply gen capacity perturbations
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
                    obj = float(net.res_cost) if hasattr(net, "res_cost") else None
                    if obj is not None:
                        all_objectives.append(obj)
                    if "lam_p" in net.res_bus.columns:
                        all_lmps.append(float(net.res_bus["lam_p"].mean()))
                else:
                    total_failed += 1

        solve_elapsed = time.perf_counter() - solve_start

        # Restore
        net.load["p_mw"] = base_loads
        net.gen["max_p_mw"] = base_gen_max

        # Memory after
        try:
            mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            results["details"]["peak_memory_mb"] = mem_after
        except Exception:
            pass

        # CPU utilization
        try:
            cpu_times = os.times()
            results["details"]["cpu_user_seconds"] = cpu_times.user
            results["details"]["cpu_system_seconds"] = cpu_times.system
        except Exception:
            pass

        # 5. Results
        results["details"]["solve_loop_seconds"] = solve_elapsed
        results["details"]["total_converged"] = total_converged
        results["details"]["total_failed"] = total_failed
        total_solves = n_scenarios * n_hours
        results["details"]["convergence_rate_pct"] = (
            total_converged / total_solves * 100 if total_solves > 0 else 0
        )
        results["details"]["per_solve_avg_seconds"] = (
            solve_elapsed / total_solves if total_solves > 0 else 0
        )

        if all_objectives:
            results["details"]["objective_stats"] = {
                "mean": float(np.mean(all_objectives)),
                "std": float(np.std(all_objectives)),
                "min": float(np.min(all_objectives)),
                "max": float(np.max(all_objectives)),
            }

        if all_lmps:
            results["details"]["lmp_stats"] = {
                "mean": float(np.mean(all_lmps)),
                "std": float(np.std(all_lmps)),
                "min": float(np.min(all_lmps)),
                "max": float(np.max(all_lmps)),
            }

        # 6. Status: qualified_pass since this is a workaround approach
        if total_converged > 0:
            results["status"] = "qualified_pass"
            results["workarounds"].append(
                "No native stochastic OPF (A-8 FAILED). This tests the B-4 "
                "loop-based workaround at SMALL scale: sequential rundcopp() calls "
                "with in-place DataFrame modification. Not a single multi-scenario "
                "optimization."
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
