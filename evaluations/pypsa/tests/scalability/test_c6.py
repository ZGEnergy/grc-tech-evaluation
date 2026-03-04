"""
Test C-6: 50-scenario stochastic DCPF at scale (SMALL — 2000-bus network)

Dimension: scalability
Network: SMALL (case_ACTIVSg2000 — 2,000 buses)
Pass condition: Completes. Record total_time, per_scenario_average.
Tool: pypsa 1.1.2

Each scenario applies a random perturbation to loads (uniform +/-20%)
and solves DCPF independently. This tests the overhead of repeatedly solving
a moderately large power flow.
"""

from __future__ import annotations

import json
import resource
import time
import traceback
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"

N_SCENARIOS = 50
LOAD_PERTURBATION = 0.20  # +/- 20%
RNG_SEED = 42


def _load_network(case_file: str) -> pypsa.Network:
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
    net.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return net


def run() -> dict:
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "peak_memory_mb": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load SMALL network
        net = _load_network("case_ACTIVSg2000.m")
        load_time = time.perf_counter() - start

        results["details"]["bus_count"] = len(net.buses)
        results["details"]["line_count"] = len(net.lines)
        results["details"]["generator_count"] = len(net.generators)
        results["details"]["load_count"] = len(net.loads)
        results["details"]["load_time_seconds"] = load_time
        results["details"]["n_scenarios"] = N_SCENARIOS

        # Store base loads
        base_loads = net.loads["p_set"].copy()

        rng = np.random.default_rng(RNG_SEED)

        scenario_times = []
        scenario_results = []
        converged_count = 0

        solve_start = time.perf_counter()

        for scenario_idx in range(N_SCENARIOS):
            # Perturb loads
            perturbation = rng.uniform(
                1.0 - LOAD_PERTURBATION,
                1.0 + LOAD_PERTURBATION,
                size=len(base_loads),
            )
            net.loads["p_set"] = base_loads * perturbation

            # Solve DCPF
            sc_start = time.perf_counter()
            net.lpf()
            sc_time = time.perf_counter() - sc_start
            scenario_times.append(sc_time)

            # Check results
            angles = net.buses_t.v_ang
            if len(angles) > 0 and angles.iloc[0].abs().max() > 1e-12:
                converged_count += 1
                total_gen = float(net.generators_t.p.iloc[0].sum())
                max_flow = float(net.lines_t.p0.iloc[0].abs().max())
                scenario_results.append(
                    {
                        "scenario": scenario_idx,
                        "total_gen_mw": total_gen,
                        "max_line_flow_mw": max_flow,
                    }
                )

        total_solve_time = time.perf_counter() - solve_start

        # Restore base loads
        net.loads["p_set"] = base_loads

        results["details"]["total_solve_time_seconds"] = total_solve_time
        results["details"]["per_scenario_average_seconds"] = total_solve_time / N_SCENARIOS
        results["details"]["scenario_time_min"] = float(min(scenario_times))
        results["details"]["scenario_time_max"] = float(max(scenario_times))
        results["details"]["scenario_time_std"] = float(np.std(scenario_times))
        results["details"]["converged_count"] = converged_count
        results["details"]["convergence_rate"] = converged_count / N_SCENARIOS

        # Sample scenario stats
        if scenario_results:
            gens = [r["total_gen_mw"] for r in scenario_results]
            flows = [r["max_line_flow_mw"] for r in scenario_results]
            results["details"]["gen_range_mw"] = [min(gens), max(gens)]
            results["details"]["max_flow_range_mw"] = [min(flows), max(flows)]

        if converged_count == N_SCENARIOS:
            results["status"] = "pass"
        elif converged_count > 0:
            results["status"] = "qualified_pass"
            results["errors"].append(f"Only {converged_count}/{N_SCENARIOS} scenarios converged")
        else:
            results["errors"].append("No scenarios converged")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        results["peak_memory_mb"] = mem_after / 1024.0

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
