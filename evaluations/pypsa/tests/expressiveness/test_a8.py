"""
Test A-8: Multi-period stochastic DC OPF with scenario-indexed timeseries

Dimension: expressiveness
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Tool natively supports scenario-indexed timeseries for load, wind,
    and solar — the stochastic structure is part of the optimization formulation
    (e.g., scenario tree, two-stage stochastic program), not just independent
    deterministic solves in a loop.
Tool: pypsa 1.1.2
Solver: HiGHS (LP)

PyPSA 1.1.x has native stochastic scenario support via n.set_scenarios() which
creates a multi-scenario optimization where scenarios are co-optimized with
probability-weighted objective. This is a genuine stochastic formulation —
all scenarios are solved in a single LP.

Workaround: PyPSA 1.1.2 has a bug in find_bus_controls() when networks with
PV-controlled generators are used with scenarios (MultiIndex key mismatch).
Monkey-patching find_bus_controls to no-op is safe for DC OPF (PV/PQ
classification only matters for AC power flow).
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"

# HiGHS solver settings (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300.0,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

# Scenario definitions
SCENARIO_NAMES = ["low", "mid", "high"]
SCENARIO_WEIGHTS = {"low": 0.25, "mid": 0.50, "high": 0.25}

# 24-hour base load profile (fraction of peak)
BASE_LOAD_PROFILE = np.array(
    [
        0.67,
        0.63,
        0.60,
        0.59,
        0.59,
        0.60,
        0.74,
        0.86,
        0.95,
        0.96,
        0.96,
        0.93,
        0.92,
        0.93,
        0.87,
        0.90,
        0.91,
        0.99,
        1.00,
        0.96,
        0.91,
        0.83,
        0.73,
        0.63,
    ]
)

# Scenario multipliers (correlated perturbation)
LOAD_MULTIPLIERS = {"low": 0.95, "mid": 1.00, "high": 1.05}
WIND_MULTIPLIERS = {"low": 1.1, "mid": 1.0, "high": 0.9}

# Base wind capacity factors (24hr, anti-correlated with load)
WIND_CF_BASE = np.array(
    [
        0.35,
        0.40,
        0.45,
        0.50,
        0.45,
        0.40,
        0.30,
        0.20,
        0.15,
        0.10,
        0.10,
        0.15,
        0.20,
        0.15,
        0.20,
        0.15,
        0.15,
        0.10,
        0.08,
        0.10,
        0.15,
        0.25,
        0.30,
        0.35,
    ]
)


def _load_network(case_file: str) -> tuple[pypsa.Network, CaseFrames]:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    cf = CaseFrames(str(DATA_DIR / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net, cf


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute the test and return structured results."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    case_file = Path(network_file).name

    start = time.perf_counter()
    try:
        # 1. Load network
        net, cf = _load_network(case_file)

        # 2. Manually assign generator costs (workaround for missing gencost import)
        gencost = cf.gencost.values
        for i, gen_name in enumerate(net.generators.index):
            if i < len(gencost):
                c2 = gencost[i, 4]
                c1 = gencost[i, 5]
                p_operating = net.generators.at[gen_name, "p_set"]
                marginal = c1 + 2 * c2 * p_operating
                net.generators.at[gen_name, "marginal_cost"] = max(marginal, 1.0)
            if net.generators.at[gen_name, "p_nom"] <= 0:
                net.generators.at[gen_name, "p_nom"] = net.generators.at[gen_name, "p_set"] * 1.5

        results["workarounds"].append(
            "Manually assigned marginal_cost from MATPOWER gencost data — "
            "PyPSA pypower importer skips gencost on import."
        )

        # 3. Add a wind generator (representative renewable with scenario variation)
        wind_capacity = 500.0  # MW
        net.add(
            "Generator",
            "Wind_25",
            bus="25",
            p_nom=wind_capacity,
            marginal_cost=0.0,
            carrier="wind",
        )

        # 4. Set up 24-hour snapshots
        snapshots = pd.date_range("2024-01-15", periods=24, freq="h")
        net.set_snapshots(snapshots)
        net.snapshot_weightings.loc[:, "objective"] = 1.0
        net.snapshot_weightings.loc[:, "generators"] = 1.0
        net.snapshot_weightings.loc[:, "stores"] = 1.0

        # Save component names before scenario duplication
        load_names = list(net.loads.index)
        gen_names = list(net.generators.index)

        # 5. Set base time-varying data (before scenarios — auto-duplicated)
        base_loads = net.loads["p_set"].copy()
        load_df_base = pd.DataFrame(
            {ln: base_loads[ln] * BASE_LOAD_PROFILE for ln in load_names},
            index=snapshots,
        )
        net.loads_t.p_set = load_df_base

        pmax_base = pd.DataFrame(
            {gn: np.ones(24) for gn in gen_names},
            index=snapshots,
        )
        pmax_base["Wind_25"] = WIND_CF_BASE
        net.generators_t.p_max_pu = pmax_base

        # 6. Workaround: Monkey-patch find_bus_controls for scenario compatibility
        # PyPSA 1.1.2 bug: find_bus_controls uses non-scenario bus index after
        # set_scenarios creates MultiIndex. Safe to skip for DC OPF.
        pypsa.networks.SubNetwork.find_bus_controls = lambda self: None

        results["workarounds"].append(
            "Monkey-patched SubNetwork.find_bus_controls to no-op — "
            "PyPSA 1.1.2 bug: find_bus_controls fails with scenario MultiIndex "
            "on pypower-imported networks (PV bus lookup uses non-scenario index). "
            "Safe for DC OPF; PV/PQ classification only matters for AC PF."
        )

        # 7. Set up stochastic scenarios using PyPSA's native API
        # After this, components are replicated per scenario
        net.set_scenarios(SCENARIO_WEIGHTS)

        results["details"]["scenarios"] = SCENARIO_NAMES
        results["details"]["scenario_weights"] = list(SCENARIO_WEIGHTS.values())
        results["details"]["has_scenarios"] = net.has_scenarios
        results["details"]["scenario_count"] = len(net.scenarios)

        # 8. Differentiate per-scenario time-varying data
        for scenario in SCENARIO_NAMES:
            # Scale loads per scenario
            for ln in load_names:
                net.loads_t.p_set[(scenario, ln)] *= LOAD_MULTIPLIERS[scenario]
            # Scale wind CF per scenario (clipped to [0, 1])
            net.generators_t.p_max_pu[(scenario, "Wind_25")] = (
                net.generators_t.p_max_pu[(scenario, "Wind_25")] * WIND_MULTIPLIERS[scenario]
            ).clip(0, 1)

        # Sanitize to add missing carriers
        net.sanitize()

        # 9. Solve stochastic DC OPF (single LP with all scenarios)
        status, termination = net.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )

        results["details"]["solver_status"] = status
        results["details"]["termination_condition"] = termination
        results["details"]["objective"] = (
            float(net.objective) if hasattr(net, "objective") else None
        )

        # 10. Extract per-scenario results from the single optimization
        scenario_results = {}
        for scenario in SCENARIO_NAMES:
            scen_gen_cols = [c for c in net.generators_t.p.columns if c[0] == scenario]
            scen_gen = net.generators_t.p[scen_gen_cols]
            total_gen = scen_gen.sum(axis=1)
            wind_col = (scenario, "Wind_25")
            wind_gen = (
                net.generators_t.p[wind_col]
                if wind_col in net.generators_t.p.columns
                else pd.Series(0.0, index=snapshots)
            )

            scenario_results[scenario] = {
                "mean_total_generation_mw": float(total_gen.mean()),
                "peak_total_generation_mw": float(total_gen.max()),
                "mean_wind_generation_mw": float(wind_gen.mean()),
                "total_generation_per_hour": [float(v) for v in total_gen.values],
            }

        results["details"]["scenario_results"] = scenario_results

        # 11. Verify stochastic structure
        gen_means = [scenario_results[s]["mean_total_generation_mw"] for s in SCENARIO_NAMES]
        dispatches_differ = max(gen_means) - min(gen_means) > 1.0
        results["details"]["dispatches_differ_across_scenarios"] = dispatches_differ
        results["details"]["generation_spread_mw"] = max(gen_means) - min(gen_means)

        wind_means = [scenario_results[s]["mean_wind_generation_mw"] for s in SCENARIO_NAMES]
        wind_differs = max(wind_means) - min(wind_means) > 0.1
        results["details"]["wind_differs_across_scenarios"] = wind_differs

        results["details"]["formulation_type"] = (
            "Probability-weighted multi-scenario DC OPF via PyPSA set_scenarios(). "
            "Scenarios are co-optimized in a single LP with scenario-indexed variables. "
            "Objective is E[cost] = sum(weight_s * cost_s). "
            "Components are internally replicated per scenario with shared topology."
        )

        # 12. Set pass status
        if (
            "ok" in str(status).lower() or "optimal" in str(termination).lower()
        ) and dispatches_differ:
            results["status"] = "pass"
        else:
            if not dispatches_differ:
                results["errors"].append(
                    "Dispatches are identical across scenarios — "
                    "stochastic structure may not be working"
                )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
