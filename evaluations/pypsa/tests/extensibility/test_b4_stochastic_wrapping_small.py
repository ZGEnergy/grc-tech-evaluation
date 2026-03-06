"""B-4 (stochastic_wrapping) -- 50-scenario stochastic DCPF on ACTIVSg2000 (SMALL).

Pass condition: Timeseries injectable via API, scenario loop without excessive overhead.
24hr multi-period with correlated perturbations.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg2000.m")
N_SCENARIOS = 50
N_HOURS = 24


def load_network(filepath: str | Path) -> pypsa.Network:
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    return n


def generate_correlated_scenarios(
    base_loads: pd.Series, n_scenarios: int, n_hours: int, seed: int = 42
) -> list[pd.DataFrame]:
    """Generate temporally correlated load scenarios with AR(1) structure."""
    rng = np.random.default_rng(seed)
    n_loads = len(base_loads)

    rho = 0.8
    time_cov = np.zeros((n_hours, n_hours))
    for i in range(n_hours):
        for j in range(n_hours):
            time_cov[i, j] = rho ** abs(i - j)

    scenarios = []
    for s in range(n_scenarios):
        perturbations = rng.multivariate_normal(np.zeros(n_hours), 0.05**2 * time_cov)
        load_variation = rng.normal(1.0, 0.02, size=n_loads)
        load_profiles = pd.DataFrame(
            np.outer(1.0 + perturbations, base_loads.values * load_variation),
            columns=base_loads.index,
        )
        scenarios.append(load_profiles)

    return scenarios


def run() -> dict:
    """Execute B-4 stochastic wrapping test on SMALL."""
    errors = []
    workarounds = []
    details = {}

    try:
        n_template = load_network(CASE_FILE)
        base_loads = n_template.loads.p_set.copy()
        details["n_loads"] = len(base_loads)
        details["n_generators"] = len(n_template.generators)
        details["n_lines"] = len(n_template.lines)
        details["base_total_load_mw"] = round(float(base_loads.sum()), 2)

        # Generate scenarios
        t_gen = time.perf_counter()
        scenarios = generate_correlated_scenarios(base_loads, N_SCENARIOS, N_HOURS)
        details["scenario_generation_seconds"] = round(time.perf_counter() - t_gen, 6)

        # Solve 24hr multi-period DCPF for each scenario
        t0 = time.perf_counter()
        scenario_results = []

        for s_idx, load_profile in enumerate(scenarios):
            n = load_network(CASE_FILE)
            snapshots = pd.date_range("2026-01-01", periods=N_HOURS, freq="h")
            n.set_snapshots(snapshots)

            for load_name in n.loads.index:
                n.loads_t.p_set[load_name] = load_profile[load_name].values

            n.lpf()

            total_gen_by_hour = n.generators_t.p.sum(axis=1)
            max_line_loading = (
                n.lines_t.p0.abs().div(n.lines.s_nom.replace(0, np.inf), axis=1)
            ).max(axis=1)

            scenario_results.append(
                {
                    "scenario": s_idx,
                    "mean_total_gen_mw": round(float(total_gen_by_hour.mean()), 2),
                    "max_line_loading": round(float(max_line_loading.max()), 4),
                }
            )

        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["n_scenarios"] = N_SCENARIOS
        details["n_hours"] = N_HOURS
        details["per_scenario_avg_seconds"] = round(wall_clock / N_SCENARIOS, 4)
        details["total_solves"] = N_SCENARIOS

        mean_gens = [r["mean_total_gen_mw"] for r in scenario_results]
        max_loadings = [r["max_line_loading"] for r in scenario_results]
        details["gen_range_across_scenarios"] = [
            round(min(mean_gens), 2),
            round(max(mean_gens), 2),
        ]
        details["max_loading_range_across_scenarios"] = [
            round(min(max_loadings), 4),
            round(max(max_loadings), 4),
        ]
        details["sample_scenarios"] = scenario_results[:3]
        details["api_method"] = (
            "Set n.set_snapshots(), assign n.loads_t.p_set per load, call n.lpf(). "
            "No config file rewriting needed."
        )

        assert len(scenario_results) == N_SCENARIOS
        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "B-4",
        "slug": "stochastic_wrapping",
        "tier": "SMALL",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
