"""C-5: N-M Contingency Sweep on MEDIUM (x=5, m=4) using graph-distance scoping."""

import time
import tracemalloc
from collections import defaultdict
from itertools import combinations

import numpy as np
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


def build_adjacency(n):
    """Build bus adjacency dict from lines."""
    adj = defaultdict(set)
    for _, line in n.lines.iterrows():
        b0, b1 = line["bus0"], line["bus1"]
        adj[b0].add(b1)
        adj[b1].add(b0)
    for _, tr in n.transformers.iterrows():
        b0, b1 = tr["bus0"], tr["bus1"]
        adj[b0].add(b1)
        adj[b1].add(b0)
    return adj


def get_neighbors(adj, buses, depth):
    """Get all buses within 'depth' hops of the given bus set."""
    visited = set(buses)
    frontier = set(buses)
    for _ in range(depth):
        new_frontier = set()
        for b in frontier:
            new_frontier.update(adj[b] - visited)
        visited.update(new_frontier)
        frontier = new_frontier
    return visited


def get_lines_in_region(n, bus_set):
    """Get lines with both endpoints in the bus set."""
    mask = n.lines["bus0"].isin(bus_set) & n.lines["bus1"].isin(bus_set)
    return n.lines.index[mask].tolist()


def main():
    print("=" * 70)
    print("C-5: N-M Contingency Sweep on MEDIUM (x=5, m=4)")
    print("=" * 70)

    n = load_network(MEDIUM)
    print(
        f"Network: {len(n.buses)} buses, {len(n.lines)} lines, {len(n.transformers)} transformers"
    )

    # Run base case DCPF
    print("\nRunning base case DCPF...")
    n.lpf()

    # Build adjacency for graph-distance scoping
    adj = build_adjacency(n)

    # Select x=5 seed lines (highest-flow lines as most critical)
    base_flows = n.lines_t.p0.iloc[0].abs()
    top_lines = base_flows.nlargest(5).index.tolist()
    print(f"Seed lines (top 5 by flow): {top_lines}")

    # For each seed line, find lines within graph distance m=4
    contingency_sets = {}
    for seed in top_lines:
        bus0 = n.lines.loc[seed, "bus0"]
        bus1 = n.lines.loc[seed, "bus1"]
        nearby_buses = get_neighbors(adj, [bus0, bus1], depth=4)
        nearby_lines = get_lines_in_region(n, nearby_buses)
        # Remove seed from candidates
        nearby_lines = [ln for ln in nearby_lines if ln != seed]
        contingency_sets[seed] = nearby_lines

    # Generate contingency cases: for each seed, trip the seed line
    # and additionally trip each nearby line (N-2 for single contingencies)
    # Plus some N-3 and N-4 combos from the scoped region
    cases_by_order = defaultdict(list)
    total_possible = 0

    for seed in top_lines:
        # N-1: just the seed
        cases_by_order[1].append((seed,))

        # N-2: seed + each neighbor
        neighbors = contingency_sets[seed][:20]  # limit to 20 neighbors
        for nb in neighbors:
            cases_by_order[2].append((seed, nb))

        # N-3: seed + pairs from top 8 neighbors
        top_nb = neighbors[:8]
        for combo in combinations(top_nb, 2):
            cases_by_order[3].append((seed,) + combo)

        # N-4: seed + triples from top 5 neighbors
        top_nb4 = neighbors[:5]
        for combo in combinations(top_nb4, 3):
            cases_by_order[4].append((seed,) + combo)

        total_possible += (
            1
            + len(neighbors)
            + len(list(combinations(top_nb, 2)))
            + len(list(combinations(top_nb4, 3)))
        )

    total_cases = sum(len(v) for v in cases_by_order.values())
    print("\nContingency cases by order:")
    for order in sorted(cases_by_order.keys()):
        print(f"  N-{order}: {len(cases_by_order[order])} cases")
    print(f"  Total: {total_cases} cases")

    # Run contingency sweep
    print("\nRunning contingency sweep...")
    tracemalloc.start()
    t_total = time.perf_counter()

    results = []
    case_times = []

    for order in sorted(cases_by_order.keys()):
        for case_lines in cases_by_order[order]:
            t_case = time.perf_counter()

            # Disable outaged lines
            for line_name in case_lines:
                if line_name in n.lines.index:
                    n.lines.loc[line_name, "active"] = False

            # Run DCPF
            try:
                n.lpf()
                case_time = time.perf_counter() - t_case
                max_flow = n.lines_t.p0.iloc[0].abs().max()
                results.append(
                    {
                        "order": order,
                        "lines": case_lines,
                        "converged": True,
                        "max_flow": max_flow,
                        "time": case_time,
                    }
                )
            except Exception as e:
                case_time = time.perf_counter() - t_case
                results.append(
                    {
                        "order": order,
                        "lines": case_lines,
                        "converged": False,
                        "error": str(e),
                        "time": case_time,
                    }
                )

            case_times.append(case_time)

            # Restore lines
            for line_name in case_lines:
                if line_name in n.lines.index:
                    n.lines.loc[line_name, "active"] = True

    total_time = time.perf_counter() - t_total
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1024 / 1024

    # Pruning ratio: total_cases / total possible N-M combos
    total_lines = len(n.lines)
    # Full N-1 would be total_lines, N-2 = C(total_lines,2), etc.
    full_n1 = total_lines
    pruning_ratio = total_cases / full_n1  # simplified

    avg_time = np.mean(case_times) if case_times else 0
    converged_count = sum(1 for r in results if r["converged"])

    print("\n--- Summary ---")
    print(f"Total cases run: {total_cases}")
    print(f"Converged: {converged_count}/{total_cases}")
    print(f"Total time: {total_time:.4f}s")
    print(f"Per-case average: {avg_time:.4f}s")
    print(f"Peak memory: {peak_mb:.2f} MB")
    print(f"Pruning ratio (cases/full_N-1): {pruning_ratio:.4f}")

    print("\nPer-order timing:")
    for order in sorted(cases_by_order.keys()):
        order_times = [r["time"] for r in results if r["order"] == order]
        if order_times:
            print(
                f"  N-{order}: {len(order_times)} cases, "
                f"avg={np.mean(order_times):.4f}s, "
                f"total={sum(order_times):.4f}s"
            )

    print("\n--- RESULTS ---")
    print(f"total_cases={total_cases}")
    print(f"total_time_s={total_time:.4f}")
    print(f"per_case_avg_s={avg_time:.4f}")
    print(f"peak_memory_mb={peak_mb:.2f}")
    print(f"converged={converged_count}")
    print(f"pruning_ratio={pruning_ratio:.4f}")
    for order in sorted(cases_by_order.keys()):
        print(f"n{order}_cases={len(cases_by_order[order])}")


if __name__ == "__main__":
    main()
