"""C-6: 50-Scenario Stochastic DCPF on SMALL (ACTIVSg2000)."""

import time
import tracemalloc

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

SMALL = "/workspace/data/networks/case_ACTIVSg2000.m"


def load_network(filepath):
    cf = CaseFrames(filepath)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0
    return n


def main():
    print("=" * 70)
    print("C-6: 50-Scenario Stochastic DCPF on SMALL (ACTIVSg2000)")
    print("=" * 70)

    n_base = load_network(SMALL)
    print(
        f"Network: {len(n_base.buses)} buses, {len(n_base.lines)} lines, "
        f"{len(n_base.generators)} generators, {len(n_base.loads)} loads"
    )

    n_scenarios = 50
    rng = np.random.RandomState(42)

    # Base load values
    base_loads = n_base.loads.p_set.copy()
    print(f"Base total load: {base_loads.sum():.2f} MW")

    tracemalloc.start()
    t_total = time.perf_counter()

    scenario_times = []
    total_gens = []
    converged_count = 0

    for i in range(n_scenarios):
        # Reload network for clean state
        n = load_network(SMALL)

        # Perturb loads: +/- 20% uniform random per load
        perturbation = rng.uniform(0.8, 1.2, size=len(n.loads))
        n.loads["p_set"] = base_loads.values * perturbation

        t_scenario = time.perf_counter()
        try:
            n.lpf()
            scenario_time = time.perf_counter() - t_scenario
            converged_count += 1
            total_gen = n.generators_t.p.values.sum()
            total_gens.append(total_gen)
        except Exception as e:
            scenario_time = time.perf_counter() - t_scenario
            if i == 0:
                print(f"  Scenario {i} failed: {e}")

        scenario_times.append(scenario_time)

        if (i + 1) % 10 == 0:
            print(
                f"  Completed {i + 1}/{n_scenarios} scenarios "
                f"(avg {np.mean(scenario_times):.4f}s/scenario)"
            )

    total_time = time.perf_counter() - t_total
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1024 / 1024

    avg_time = np.mean(scenario_times)
    print("\n--- Summary ---")
    print(f"Scenarios: {n_scenarios}")
    print(f"Converged: {converged_count}/{n_scenarios}")
    print(f"Total time: {total_time:.4f}s")
    print(f"Per-scenario average: {avg_time:.4f}s")
    print(f"Peak memory: {peak_mb:.2f} MB")
    if total_gens:
        print(f"Generation range: [{min(total_gens):.2f}, {max(total_gens):.2f}] MW")
        print(f"Generation std: {np.std(total_gens):.2f} MW")

    print("\n--- RESULTS ---")
    print(f"n_scenarios={n_scenarios}")
    print(f"total_time_s={total_time:.4f}")
    print(f"per_scenario_avg_s={avg_time:.4f}")
    print(f"peak_memory_mb={peak_mb:.2f}")
    print(f"converged={converged_count}")


if __name__ == "__main__":
    main()
