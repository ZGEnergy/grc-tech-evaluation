"""B-4: Stochastic Wrapping on ACTIVSg2000 (SMALL).

Dimension: extensibility
Network: SMALL (ACTIVSg 2000-bus)
Pass condition: Generate 20 scenarios with correlated perturbations by resource type;
solve 12hr multi-period DCOPF for each; collect prices and dispatch.
Tool accepts timeseries inputs programmatically (not config files only).
Scenario loop expressible without excessive overhead.

NOTE: Time-series OPF expected to crash with TapPhaseControl error (same as TINY).
Workaround: snapshot OPF in a loop per scenario/hour.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg2000.m")

N_SCENARIOS = 20
N_HOURS = 12


def run() -> dict:
    """Execute B-4 stochastic wrapping test on SMALL network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "SMALL (ACTIVSg2000)"

        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)

        # ── Step 1: Classify generators by resource type (cost proxy) ──
        n_gen = len(grid.generators)
        gen_data = []
        for i, g in enumerate(grid.generators):
            gen_data.append(
                {
                    "index": i,
                    "name": g.name,
                    "Cost": g.Cost,
                    "Pmax": g.Pmax,
                }
            )

        costs = [g["Cost"] for g in gen_data]
        cost_sorted = sorted(range(len(costs)), key=lambda i: costs[i])
        resource_map = {}
        for rank, idx in enumerate(cost_sorted):
            if rank < n_gen // 3:
                resource_map[idx] = "baseload"
            elif rank < 2 * n_gen // 3:
                resource_map[idx] = "intermediate"
            else:
                resource_map[idx] = "peaker"

        type_counts = {}
        for v in resource_map.values():
            type_counts[v] = type_counts.get(v, 0) + 1
        details["resource_type_counts"] = type_counts

        # ── Step 2: Generate correlated scenarios ──
        np.random.seed(42)

        load_profile = np.array(
            [
                0.85,
                0.80,
                0.78,
                0.80,
                0.85,
                0.92,
                0.98,
                1.00,
                0.97,
                0.95,
                0.93,
                0.90,
            ]
        )

        scenarios = []
        for s in range(N_SCENARIOS):
            type_factors = {}
            for rt in ["baseload", "intermediate", "peaker"]:
                common = 0.05 * np.random.randn()
                type_factors[rt] = np.clip(1.0 + common + 0.03 * np.random.randn(N_HOURS), 0.7, 1.3)

            load_factor = np.clip(1.0 + 0.05 * np.random.randn(N_HOURS), 0.8, 1.2)

            scenarios.append(
                {
                    "gen_factors": {i: type_factors[resource_map[i]] for i in range(n_gen)},
                    "load_factor": load_factor,
                }
            )

        details["scenarios_generated"] = N_SCENARIOS

        # ── Step 3: Try time-series OPF first ──
        ts_opf_works = False
        try:
            import pandas as pd

            grid_ts = vge.open_file(NETWORK_FILE)
            time_idx = pd.date_range("2025-01-01", periods=N_HOURS, freq="h")
            grid_ts.time_profile = time_idx

            for ld in grid_ts.loads:
                ld.P_prof = ld.P * scenarios[0]["load_factor"]
                ld.Q_prof = ld.Q * scenarios[0]["load_factor"]

            for i, gen in enumerate(grid_ts.generators):
                gen.Pmax_prof = np.full(N_HOURS, gen.Pmax) * scenarios[0]["gen_factors"][i]

            opf_vars, lp_model = vge.run_linear_opf_ts(
                grid_ts,
                time_indices=np.arange(N_HOURS),
                solver_type=MIPSolvers.HIGHS,
            )
            ts_opf_works = True
            details["ts_opf_test"] = "succeeded"
        except Exception as e:
            details["ts_opf_test"] = f"failed: {type(e).__name__}: {e}"
            workarounds.append(
                {
                    "description": (
                        "Time-series OPF crashes with TapPhaseControl error. "
                        "Using hour-by-hour snapshot OPF loop as workaround."
                    ),
                    "class": "fragile",
                    "reason": "Known GridCal bug on transformer handling in TS-OPF.",
                }
            )

        # ── Step 4: Scenario loop with snapshot OPF per hour ──
        t0 = time.perf_counter()

        scenario_results = []
        for s_idx, scenario in enumerate(scenarios):
            hourly_dispatch = np.zeros((N_HOURS, n_gen))
            hourly_prices = np.zeros((N_HOURS, grid.get_bus_number()))
            converged_hours = 0

            for h in range(N_HOURS):
                # Re-load grid for clean state per hour
                grid_h = vge.open_file(NETWORK_FILE)

                # Apply load scaling
                for ld in grid_h.loads:
                    ld.P = ld.P * float(scenario["load_factor"][h]) * load_profile[h]
                    ld.Q = ld.Q * float(scenario["load_factor"][h]) * load_profile[h]

                # Apply generator perturbations
                for i, gen in enumerate(grid_h.generators):
                    factor = float(scenario["gen_factors"][i][h])
                    gen.Pmax = gen.Pmax * factor

                opts = vge.OptimalPowerFlowOptions()
                opts.mip_solver = MIPSolvers.HIGHS

                try:
                    res = vge.linear_opf(grid_h, options=opts)
                    if res.converged:
                        hourly_dispatch[h] = res.generator_power
                        hourly_prices[h] = res.bus_shadow_prices
                        converged_hours += 1
                except Exception:
                    pass

            scenario_results.append(
                {
                    "scenario": s_idx,
                    "converged_hours": converged_hours,
                    "total_hours": N_HOURS,
                    "dispatch_mean_mw": round(float(hourly_dispatch.mean()), 2),
                    "price_mean": round(float(hourly_prices.mean()), 6),
                    "price_std": round(float(hourly_prices.std()), 6),
                }
            )

            # Progress indicator
            if (s_idx + 1) % 5 == 0:
                elapsed = time.perf_counter() - t0
                print(f"  Scenario {s_idx + 1}/{N_SCENARIOS} done ({elapsed:.1f}s elapsed)")

        wall_clock = time.perf_counter() - t0
        details["wall_clock_seconds"] = round(wall_clock, 4)

        # ── Aggregate results ──
        all_converged = all(sr["converged_hours"] == N_HOURS for sr in scenario_results)
        total_solves = sum(sr["converged_hours"] for sr in scenario_results)
        details["total_solves"] = total_solves
        details["total_expected"] = N_SCENARIOS * N_HOURS
        details["all_scenarios_converged"] = all_converged
        details["per_solve_avg_ms"] = round(wall_clock / max(total_solves, 1) * 1000, 2)

        # Price distribution across scenarios
        mean_prices = [sr["price_mean"] for sr in scenario_results]
        details["price_distribution"] = {
            "mean": round(float(np.mean(mean_prices)), 6),
            "std": round(float(np.std(mean_prices)), 6),
            "min": round(float(np.min(mean_prices)), 6),
            "max": round(float(np.max(mean_prices)), 6),
        }

        details["scenario_summary"] = scenario_results

        # ── Assess pass condition ──
        if all_converged:
            if ts_opf_works:
                status = "pass"
                details["pass_rationale"] = (
                    f"Time-series OPF works; {N_SCENARIOS} scenarios x {N_HOURS} hours solved "
                    f"on 2000-bus network in {round(wall_clock, 1)}s."
                )
            else:
                status = "qualified_pass"
                details["pass_rationale"] = (
                    f"{total_solves} snapshot OPFs solved ({N_SCENARIOS} scenarios x {N_HOURS} hours) "
                    f"on 2000-bus network in {round(wall_clock, 1)}s. "
                    "Uses snapshot OPF loop due to TapPhaseControl crash. No inter-temporal constraints."
                )
        else:
            status = "fail"
            errors.append(
                f"Not all scenarios fully converged: {total_solves}/{N_SCENARIOS * N_HOURS}"
            )

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    # Print summary without full scenario details
    summary = {k: v for k, v in result.items() if k != "details"}
    summary["details"] = {k: v for k, v in result["details"].items() if k != "scenario_summary"}
    print(json.dumps(summary, indent=2, default=str))
