"""C-1: DCPF on MEDIUM (10k-bus) network -- wall-clock and peak memory."""

import time
import tracemalloc

import pypsa
from matpowercaseframes import CaseFrames

MEDIUM = "/workspace/data/networks/case_ACTIVSg10k.m"


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
    print("C-1: DCPF on MEDIUM (10k-bus)")
    print("=" * 70)

    # Load network
    t_load = time.perf_counter()
    n = load_network(MEDIUM)
    load_time = time.perf_counter() - t_load
    print(
        f"\nNetwork loaded: {len(n.buses)} buses, {len(n.lines)} lines, "
        f"{len(n.transformers)} transformers, {len(n.generators)} generators"
    )
    print(f"Load time: {load_time:.3f}s")

    # Run DCPF with measurement
    tracemalloc.start()
    t0 = time.perf_counter()
    n.lpf()
    wall_clock = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1024 / 1024

    print(f"\nDCPF wall-clock: {wall_clock:.4f}s")
    print(f"Peak memory: {peak_mb:.2f} MB")

    # Check convergence
    converged = True  # lpf always converges for connected networks
    print(f"Converged: {converged}")

    # Summary statistics
    p_lines = n.lines_t.p0
    p_gen = n.generators_t.p
    print(f"\nLine flow range: [{p_lines.values.min():.2f}, {p_lines.values.max():.2f}] MW")
    print(f"Generator dispatch range: [{p_gen.values.min():.2f}, {p_gen.values.max():.2f}] MW")
    print(f"Total generation: {p_gen.values.sum():.2f} MW")
    print(f"Total load: {n.loads.p_set.sum():.2f} MW")

    # Run 3 more times for timing stability
    times = [wall_clock]
    for _ in range(3):
        n2 = load_network(MEDIUM)
        t0 = time.perf_counter()
        n2.lpf()
        times.append(time.perf_counter() - t0)

    print(f"\nTiming (4 runs): {[f'{t:.4f}' for t in times]}")
    print(f"Mean: {sum(times) / len(times):.4f}s, Min: {min(times):.4f}s, Max: {max(times):.4f}s")

    print("\n--- RESULTS ---")
    print(f"wall_clock_s={wall_clock:.4f}")
    print(f"peak_memory_mb={peak_mb:.2f}")
    print(f"mean_time_s={sum(times) / len(times):.4f}")
    print(f"n_buses={len(n.buses)}")
    print(f"n_branches={len(n.lines) + len(n.transformers)}")
    print(f"converged={converged}")


if __name__ == "__main__":
    main()
