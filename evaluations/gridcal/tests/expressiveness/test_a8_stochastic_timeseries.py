"""A-8: Stochastic Time-series DCOPF on IEEE 39-bus (TINY).

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Tool natively supports scenario-indexed timeseries for load, wind,
and solar — the stochastic structure is part of the optimization formulation
(e.g., scenario tree, two-stage stochastic program), not just independent
deterministic solves in a loop. Perturbations are independent by resource type.
Prices extractable from solution.
Tool: gridcal (VeraGridEngine)
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")

N_SCENARIOS = 5
N_HOURS = 12


def run() -> dict:
    """Execute A-8 stochastic timeseries DCOPF test."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import pandas as pd
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # Load network
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)

        # ── Check 1: Does GridCal have native stochastic programming? ──
        # Research indicates: GridCal has StochasticPowerFlowDriver (Monte Carlo)
        # but NOT scenario-tree or two-stage stochastic OPF.
        has_stochastic_opf = False

        # Check for stochastic OPF capabilities in the API
        stochastic_classes = []
        for attr in dir(vge):
            if "stochastic" in attr.lower() or "scenario" in attr.lower():
                stochastic_classes.append(attr)
        details["stochastic_api_surface"] = stochastic_classes

        # Check if OptimalPowerFlowTimeSeriesDriver supports scenarios
        try:
            from VeraGridEngine.Simulations.OPF.opf_ts_driver import (
                OptimalPowerFlowTimeSeriesDriver,
            )

            details["opf_ts_driver_exists"] = True
        except ImportError:
            details["opf_ts_driver_exists"] = False

        # Check OPF options for scenario-related settings
        opts = vge.OptimalPowerFlowOptions()
        scenario_attrs = [a for a in dir(opts) if "scenario" in a.lower() or "stoch" in a.lower()]
        details["opf_scenario_options"] = scenario_attrs

        details["native_stochastic_opf"] = has_stochastic_opf
        details["native_assessment"] = (
            "GridCal does NOT have native stochastic programming (scenario-tree, "
            "two-stage stochastic OPF). It has StochasticPowerFlowDriver which is "
            "Monte Carlo simulation of power flow, not stochastic optimization. "
            "The OPF time-series driver solves deterministic multi-period problems."
        )

        # ── Check 2: Can we do loop-based stochastic DCOPF? ──
        # This is a workaround — not native stochastic programming
        details["loop_workaround_attempted"] = True

        # Classify generators by cost for independent perturbations
        gen_costs = [(i, g.name, g.Cost) for i, g in enumerate(grid.generators)]
        costs_sorted = sorted(gen_costs, key=lambda x: x[2])
        n_gen = len(costs_sorted)
        q1 = n_gen // 4
        q3 = 3 * n_gen // 4

        resource_types = {}
        for i, (idx, name, cost) in enumerate(costs_sorted):
            if cost <= 0.01:
                resource_types[idx] = "renewable"
            elif i < q1:
                resource_types[idx] = "baseload"
            elif i < q3:
                resource_types[idx] = "intermediate"
            else:
                resource_types[idx] = "peaker"

        type_counts = {}
        for rt in resource_types.values():
            type_counts[rt] = type_counts.get(rt, 0) + 1
        details["resource_type_counts"] = type_counts

        # Generate scenarios with independent perturbations by resource type
        np.random.seed(42)
        scenario_results = []

        # Set up time series profiles on the grid
        time_idx = pd.DatetimeIndex(pd.date_range("2024-01-01", periods=N_HOURS, freq="h"))
        grid.time_profile = time_idx

        # Set load profiles (base variation)
        t0 = time.perf_counter()

        for s in range(N_SCENARIOS):
            # Generate perturbation factors by resource type
            perturbations = {}
            for rt in set(resource_types.values()):
                perturbations[rt] = 1.0 + 0.1 * np.random.randn(N_HOURS)
                perturbations[rt] = np.clip(perturbations[rt], 0.5, 1.5)

            # Load perturbation (common across all loads)
            load_factor = 1.0 + 0.05 * np.random.randn(N_HOURS)
            load_factor = np.clip(load_factor, 0.7, 1.3)

            # Apply profiles to generators
            for i, gen in enumerate(grid.generators):
                rt = resource_types.get(i, "intermediate")
                gen.P_prof = gen.P * perturbations[rt]

            # Apply load profiles
            for i, ld in enumerate(grid.loads):
                ld.P_prof = ld.P * load_factor

            # Solve multi-period DC OPF
            opf_opts = vge.OptimalPowerFlowOptions()
            opf_opts.mip_solver = MIPSolvers.HIGHS

            try:
                from VeraGridEngine.Simulations.OPF.opf_ts_driver import (
                    OptimalPowerFlowTimeSeriesDriver,
                )

                driver = OptimalPowerFlowTimeSeriesDriver(
                    grid=grid,
                    options=opf_opts,
                    time_indices=list(range(N_HOURS)),
                )
                driver.run()
                results = driver.results

                if results is not None and results.converged is not None:
                    scenario_results.append(
                        {
                            "scenario": s,
                            "converged": bool(np.all(results.converged)),
                            "shadow_prices_shape": list(results.bus_shadow_prices.shape)
                            if hasattr(results, "bus_shadow_prices")
                            and results.bus_shadow_prices is not None
                            else None,
                            "gen_power_shape": list(results.generator_power.shape)
                            if hasattr(results, "generator_power")
                            and results.generator_power is not None
                            else None,
                        }
                    )
                else:
                    scenario_results.append(
                        {
                            "scenario": s,
                            "converged": False,
                            "error": "Results object is None or has no convergence info",
                        }
                    )
            except Exception as e:
                scenario_results.append(
                    {
                        "scenario": s,
                        "converged": False,
                        "error": f"{type(e).__name__}: {e}",
                    }
                )

        wall_clock = time.perf_counter() - t0
        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["scenario_results"] = scenario_results
        details["scenarios_converged"] = sum(1 for r in scenario_results if r.get("converged"))

        # ── Determine status ──
        # The pass condition requires NATIVE stochastic programming support
        # Loop-based workaround does NOT satisfy the pass condition
        status = "fail"
        details["failure_reason"] = (
            "GridCal does not support native scenario-indexed stochastic optimization. "
            "The stochastic structure (scenario tree, two-stage stochastic program) is "
            "not part of the optimization formulation. Only loop-based deterministic "
            "solves are possible, which the pass condition explicitly excludes."
        )

        workarounds.append(
            {
                "description": (
                    "Loop-based multi-scenario DCOPF using OptimalPowerFlowTimeSeriesDriver. "
                    "Each scenario is solved independently — no joint optimization across scenarios. "
                    "This does NOT satisfy the pass condition for native stochastic programming."
                ),
                "class": "blocking",
                "reason": (
                    "GridCal's OPF formulation has no scenario indexing or stochastic structure. "
                    "Implementing true stochastic programming would require modifying the MIP "
                    "formulation source code."
                ),
            }
        )

    except Exception as e:
        errors.append(f"Exception: {type(e).__name__}: {e}")
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
    print(json.dumps(result, indent=2, default=str))
