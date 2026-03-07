"""
Test C-6: 20-scenario stochastic DCOPF (12hr, independent perturbations by resource type)
on SMALL (ACTIVSg 2000-bus)

Dimension: scalability
Network: SMALL (ACTIVSg2000)
Pass condition: Completes. Total and per-scenario times recorded. Prices extracted.
    Uses deterministic scenario LOOP approach (PyPSA has no native stochastic optimization
    for this use case).
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
    costs_set = 0
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])
            if cost_type == 2 and n_coeffs >= 2:
                c1 = float(cost_row[4 + n_coeffs - 2])
                perturbation = rng.uniform(-0.1, 0.1) * c1
                net.generators.loc[gen_idx, "marginal_cost"] = c1 + perturbation
                costs_set += 1

    return net, costs_set


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


def _get_peak_memory_mb():
    """Get peak memory usage in MB using resource module."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024.0  # Linux returns KB
    except Exception:
        return None


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute 20-scenario stochastic DCOPF on 2000-bus network.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start_total = time.perf_counter()
    try:
        import pypsa

        _get_peak_memory_mb()

        # 1. Load base network
        n_base, costs_set = _load_network_with_costs(network_file)
        if costs_set > 0:
            results["workarounds"].append(
                f"Manually set marginal_cost on {costs_set}/{len(n_base.generators)} "
                "generators from gencost data (PPC importer does not import gencost)"
            )

        network_stats = {
            "n_buses": len(n_base.buses),
            "n_generators": len(n_base.generators),
            "n_lines": len(n_base.lines),
            "n_transformers": len(n_base.transformers),
            "n_loads": len(n_base.loads),
        }

        # Set up 12 hourly snapshots
        snapshots = pd.date_range("2024-01-01", periods=N_HOURS, freq="h")
        n_base.set_snapshots(snapshots)

        # Set time-varying loads (constant base, scaled per scenario)
        base_loads = n_base.loads["p_set"].copy()
        load_df = pd.DataFrame(
            {load_idx: base_loads[load_idx] for load_idx in n_base.loads.index},
            index=snapshots,
        )
        n_base.loads_t.p_set = load_df

        # Classify generators by resource type
        gen_types = _classify_generators(n_base)

        # 2. Generate 20 scenarios with independent perturbations by resource type
        rng = np.random.default_rng(seed=RNG_SEED)
        scenarios = []
        for _ in range(N_SCENARIOS):
            scenarios.append(
                {
                    "load_factor": rng.uniform(0.92, 1.08),
                    "gen_factors": {
                        "baseload": rng.uniform(0.97, 1.03),
                        "intermediate": rng.uniform(0.93, 1.07),
                        "peaker": rng.uniform(0.90, 1.10),
                    },
                }
            )

        # 3. Solve each scenario
        all_lmps = []
        all_objectives = []
        scenario_times = []
        n_failed = 0

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

            # Apply generator capacity perturbations by resource type
            for gen_idx in n.generators.index:
                if gen_idx in gen_types:
                    gtype = gen_types[gen_idx]
                    if gtype in scenario["gen_factors"]:
                        factor = scenario["gen_factors"][gtype]
                        p_nom = n_base.generators.loc[gen_idx, "p_nom"]
                        n.generators.loc[gen_idx, "p_nom"] = p_nom * factor

            # Solve DCOPF
            t0 = time.perf_counter()
            try:
                status = n.optimize(solver_name=SOLVER_NAME, solver_options=SOLVER_OPTIONS)
                t1 = time.perf_counter()
                scenario_times.append(t1 - t0)

                converged = "ok" in str(status).lower() or "optimal" in str(status).lower()
                if not converged:
                    results["errors"].append(f"Scenario {s_idx} did not converge: {status}")
                    n_failed += 1
                    continue

                # Collect LMPs
                lmp_snapshot = n.buses_t.marginal_price.mean().to_dict()
                lmp_snapshot["scenario"] = s_idx
                all_lmps.append(lmp_snapshot)

                all_objectives.append(float(n.objective))
            except Exception as scenario_err:
                t1 = time.perf_counter()
                scenario_times.append(t1 - t0)
                n_failed += 1
                results["errors"].append(
                    f"Scenario {s_idx} error: {type(scenario_err).__name__}: {scenario_err}"
                )

        elapsed_total = time.perf_counter() - start_total
        mem_after = _get_peak_memory_mb()

        # 4. Aggregate results
        n_solved = len(all_objectives)
        time_arr = np.array(scenario_times) if scenario_times else np.array([0.0])

        lmp_summary = {}
        if all_lmps:
            lmp_df = pd.DataFrame(all_lmps)
            lmp_cols = [c for c in lmp_df.columns if c != "scenario"]
            lmp_values = lmp_df[lmp_cols].values
            lmp_summary = {
                "mean_lmp": float(np.nanmean(lmp_values)),
                "std_lmp": float(np.nanstd(lmp_values)),
                "min_lmp": float(np.nanmin(lmp_values)),
                "max_lmp": float(np.nanmax(lmp_values)),
            }

        obj_summary = {}
        if all_objectives:
            obj_arr = np.array(all_objectives)
            obj_summary = {
                "objective_mean": float(obj_arr.mean()),
                "objective_std": float(obj_arr.std()),
                "objective_min": float(obj_arr.min()),
                "objective_max": float(obj_arr.max()),
            }

        results["wall_clock_seconds"] = elapsed_total
        results["details"] = {
            "n_scenarios_requested": N_SCENARIOS,
            "n_scenarios_solved": n_solved,
            "n_scenarios_failed": n_failed,
            "n_hours": N_HOURS,
            "solver": SOLVER_NAME,
            "network": network_stats,
            "total_wall_clock_s": elapsed_total,
            "solve_time_total_s": float(time_arr.sum()),
            "solve_time_mean_s": float(time_arr.mean()),
            "solve_time_std_s": float(time_arr.std()),
            "solve_time_min_s": float(time_arr.min()),
            "solve_time_max_s": float(time_arr.max()),
            "per_scenario_times_s": [float(t) for t in scenario_times],
            "lmp_summary": lmp_summary,
            "objective_summary": obj_summary,
            "peak_memory_mb": mem_after if mem_after else None,
            "pypsa_version": pypsa.__version__,
        }

        # Pass condition: all scenarios complete, times + prices recorded
        if n_solved == N_SCENARIOS:
            results["status"] = "pass"
        elif n_solved >= N_SCENARIOS * 0.9:
            results["status"] = "qualified_pass"
            results["workarounds"].append(f"{n_failed}/{N_SCENARIOS} scenarios failed to converge")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["wall_clock_seconds"] = time.perf_counter() - start_total

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
