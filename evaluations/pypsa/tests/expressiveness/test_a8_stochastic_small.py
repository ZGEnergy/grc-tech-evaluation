"""A-8 (stochastic_timeseries) -- Deterministic scenario loop on ACTIVSg2000 (SMALL).

On TINY, native set_scenarios() failed due to pypower import bug (PARTIAL).
On SMALL, test the deterministic scenario loop as workaround (B-4 style).
Record as qualified_pass if loop works.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg2000.m")
N_SCENARIOS = 5
N_HOURS = 24


def load_network_with_costs(filepath: str | Path) -> pypsa.Network:
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    if hasattr(cf, "gencost") and cf.gencost is not None:
        ppc["gencost"] = cf.gencost.values
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)

    if hasattr(cf, "gencost") and cf.gencost is not None:
        gc = cf.gencost.values
        for i, gen_name in enumerate(n.generators.index):
            if i < len(gc):
                cost_type = int(gc[i, 0])
                if cost_type == 2:
                    n_coeffs = int(gc[i, 3])
                    if n_coeffs == 2:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 4]
                    elif n_coeffs >= 3:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 5]
    return n


def run() -> dict:
    """Execute A-8 stochastic timeseries test on SMALL via deterministic loop."""
    errors = []
    workarounds = []
    details = {}

    workarounds.append(
        {
            "type": "stable",
            "description": (
                "Native set_scenarios() fails with pypower-imported networks (PARTIAL on TINY). "
                "Using deterministic scenario loop as workaround: solve DC OPF per scenario "
                "with perturbed loads. This tests timeseries injection API at scale."
            ),
        }
    )

    try:
        n_template = load_network_with_costs(CASE_FILE)
        base_loads = n_template.loads.p_set.copy()
        details["n_loads"] = len(base_loads)
        details["n_generators"] = len(n_template.generators)
        details["base_total_load_mw"] = round(float(base_loads.sum()), 2)

        perturbations = [0.85, 0.92, 1.0, 1.08, 1.15]

        load_profile = np.array(
            [
                0.65,
                0.60,
                0.58,
                0.56,
                0.58,
                0.65,
                0.78,
                0.90,
                0.95,
                0.98,
                1.00,
                0.99,
                0.97,
                0.96,
                0.95,
                0.96,
                0.98,
                1.00,
                0.99,
                0.95,
                0.90,
                0.82,
                0.75,
                0.68,
            ]
        )

        t0 = time.perf_counter()
        scenario_results = []

        for s_idx, pert in enumerate(perturbations):
            n = load_network_with_costs(CASE_FILE)
            snapshots = pd.date_range("2026-01-01", periods=N_HOURS, freq="h")
            n.set_snapshots(snapshots)

            # Inject time-varying, scenario-perturbed loads
            for load_name in n.loads.index:
                n.loads_t.p_set[load_name] = base_loads[load_name] * load_profile * pert

            # Solve DC OPF for this scenario
            ts = time.perf_counter()
            status_result = n.optimize(
                solver_name="highs",
                solver_options={"time_limit": 120, "presolve": "on", "threads": 1},
            )
            scenario_time = time.perf_counter() - ts

            scenario_results.append(
                {
                    "scenario": s_idx,
                    "perturbation": pert,
                    "solver_status": str(status_result),
                    "objective": round(float(n.objective), 2),
                    "wall_clock": round(scenario_time, 4),
                }
            )

        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["n_scenarios"] = N_SCENARIOS
        details["n_hours"] = N_HOURS
        details["per_scenario_avg_seconds"] = round(wall_clock / N_SCENARIOS, 4)
        details["scenario_results"] = scenario_results
        details["all_solved"] = all(
            "optimal" in r["solver_status"].lower() for r in scenario_results
        )
        details["method"] = (
            "Deterministic loop: fresh network per scenario, inject loads via "
            "n.loads_t.p_set, solve DC OPF. Workaround for set_scenarios() bug."
        )

        status = "QUALIFIED_PASS" if details["all_solved"] else "PARTIAL"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "A-8",
        "slug": "stochastic_timeseries",
        "tier": "SMALL",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", round(wall_clock, 4)),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
