"""
Interactive contingency sweep latency benchmark.

Simulates the exact user workflow:
  1. User clicks a bus on the map
  2. BFS out to h hops → find scoped branches
  3. Enumerate N-m contingencies (m=1,2,3) over scoped branches
  4. Compute all post-contingency flows via BODF
  5. Detect violations

Measures wall-clock latency for steps 2-5 at 39, 2000, 10000 buses
and h = 1, 2, 3, 4 hops.
"""

from __future__ import annotations

import gc
import itertools
import json
import time
from pathlib import Path

import networkx as nx
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORKS = {
    "case39": str(REPO_ROOT / "data" / "networks" / "case39.m"),
    "case2000": str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m"),
    "case10000": str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m"),
}


def load_and_prepare(network_file: str):
    """Load network, run DCPF, compute BODF. Returns prepared context."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=1.0)

    # DCPF
    n.lpf()

    # Topology + BODF
    n.determine_network_topology()
    for sn in n.sub_networks.obj:
        sn.calculate_PTDF()
        sn.calculate_BODF()

    # Get main sub-network
    main_sn = max(n.sub_networks.obj, key=lambda sn: len(sn.branches()))
    sn_branches = main_sn.branches()
    BODF = main_sn.BODF

    # Build p0 and s_nom vectors
    p0 = []
    s_nom = []
    for comp, bname in sn_branches.index:
        if comp == "Line" and bname in n.lines_t.p0.columns:
            p0.append(float(n.lines_t.p0.iloc[0][bname]))
        elif (
            comp == "Transformer"
            and len(n.transformers_t.p0) > 0
            and bname in n.transformers_t.p0.columns
        ):
            p0.append(float(n.transformers_t.p0.iloc[0][bname]))
        else:
            p0.append(0.0)

        if comp == "Line" and bname in n.lines.index:
            s_nom.append(float(n.lines.at[bname, "s_nom"]))
        elif comp == "Transformer" and bname in n.transformers.index:
            s_nom.append(float(n.transformers.at[bname, "s_nom"]))
        else:
            s_nom.append(1e9)

    p0 = np.array(p0)
    s_nom = np.array(s_nom)

    # Build branch index lookup: branch_name -> position in BODF matrix
    branch_idx = {}
    for i, (comp, bname) in enumerate(sn_branches.index):
        branch_idx[(comp, bname)] = i

    return n, BODF, p0, s_nom, branch_idx


def bfs_scoped_branches(n, focal_bus: str, h: int, branch_idx: dict) -> list[int]:
    """BFS from focal_bus out to h hops. Return BODF column indices of scoped branches."""
    G = n.graph()
    if focal_bus not in G:
        return []

    distance = nx.single_source_shortest_path_length(G, focal_bus, cutoff=h)
    buses_in_scope = set(distance.keys())

    scoped = []
    for line_name in n.lines.index:
        key = ("Line", line_name)
        if key not in branch_idx:
            continue
        bus0 = n.lines.at[line_name, "bus0"]
        bus1 = n.lines.at[line_name, "bus1"]
        if bus0 in buses_in_scope or bus1 in buses_in_scope:
            scoped.append(branch_idx[key])

    return scoped


def sweep_n1(
    BODF: np.ndarray, p0: np.ndarray, s_nom: np.ndarray, scoped_indices: list[int]
) -> tuple[np.ndarray, int]:
    """N-1 sweep via BODF. Returns (max_loading_per_contingency, n_violations)."""
    k_indices = np.array(scoped_indices)
    # Vectorized: post_flows[:, j] = p0 + BODF[:, k_j] * p0[k_j]
    bodf_cols = BODF[:, k_indices]  # (n_branches, n_contingencies)
    p0_outaged = p0[k_indices]  # (n_contingencies,)
    delta = bodf_cols * p0_outaged[np.newaxis, :]  # broadcast
    post_flows = p0[:, np.newaxis] + delta  # (n_branches, n_contingencies)
    violations = np.abs(post_flows) > s_nom[:, np.newaxis]
    return post_flows, int(violations.sum())


def sweep_n2(
    BODF: np.ndarray, p0: np.ndarray, s_nom: np.ndarray, scoped_indices: list[int]
) -> tuple[int, int]:
    """N-2 sweep via BODF superposition. Returns (n_combinations, n_violations)."""
    pairs = list(itertools.combinations(scoped_indices, 2))
    n_pairs = len(pairs)

    if n_pairs == 0:
        return 0, 0

    # Vectorized: for each pair (k1, k2), delta = BODF[:,k1]*p0[k1] + BODF[:,k2]*p0[k2]
    k1s = np.array([p[0] for p in pairs])
    k2s = np.array([p[1] for p in pairs])
    delta = BODF[:, k1s] * p0[k1s][np.newaxis, :] + BODF[:, k2s] * p0[k2s][np.newaxis, :]
    post_flows = p0[:, np.newaxis] + delta
    violations = np.abs(post_flows) > s_nom[:, np.newaxis]
    return n_pairs, int(violations.sum())


def sweep_n3(
    BODF: np.ndarray,
    p0: np.ndarray,
    s_nom: np.ndarray,
    scoped_indices: list[int],
    max_combos: int = 50000,
) -> tuple[int, int]:
    """N-3 sweep via BODF superposition. Caps at max_combos to avoid OOM."""
    triples = list(itertools.islice(itertools.combinations(scoped_indices, 3), max_combos))
    n_triples = len(triples)

    if n_triples == 0:
        return 0, 0

    k1s = np.array([t[0] for t in triples])
    k2s = np.array([t[1] for t in triples])
    k3s = np.array([t[2] for t in triples])
    delta = (
        BODF[:, k1s] * p0[k1s][np.newaxis, :]
        + BODF[:, k2s] * p0[k2s][np.newaxis, :]
        + BODF[:, k3s] * p0[k3s][np.newaxis, :]
    )
    post_flows = p0[:, np.newaxis] + delta
    violations = np.abs(post_flows) > s_nom[:, np.newaxis]
    return n_triples, int(violations.sum())


def run_sweep(label: str, network_file: str, hop_range: list[int]) -> dict:
    """Run the full interactive sweep benchmark for one network."""
    print(f"\n{'=' * 60}")
    print(f"Network: {label}")
    print(f"{'=' * 60}")

    # Startup (one-time cost)
    t0 = time.perf_counter()
    n, BODF, p0, s_nom, branch_idx = load_and_prepare(network_file)
    startup = time.perf_counter() - t0
    n_buses = len(n.buses)
    n_branches = BODF.shape[0]
    print(f"Startup: {startup:.2f}s ({n_buses} buses, {n_branches} branches)")
    print(f"BODF shape: {BODF.shape}, memory: {BODF.nbytes / 1024 / 1024:.0f} MB")

    # Pick focal bus: highest degree (worst case for scoping)
    G = n.graph()
    degrees = dict(G.degree())
    focal_bus = max(degrees, key=lambda b: degrees[b])
    focal_degree = degrees[focal_bus]

    # Also pick a median-degree bus for typical case
    sorted_buses = sorted(degrees.items(), key=lambda x: x[1])
    median_bus = sorted_buses[len(sorted_buses) // 2][0]
    median_degree = degrees[median_bus]

    print(f"Focal bus (max degree): {focal_bus} (degree={focal_degree})")
    print(f"Median bus: {median_bus} (degree={median_degree})")

    result = {
        "n_buses": n_buses,
        "n_branches": n_branches,
        "startup_s": startup,
        "bodf_memory_mb": BODF.nbytes / 1024 / 1024,
        "focal_bus": focal_bus,
        "focal_degree": focal_degree,
        "median_bus": median_bus,
        "median_degree": median_degree,
        "sweeps": {},
    }

    for bus_label, bus_id in [("max_degree", focal_bus), ("median_degree", median_bus)]:
        print(f"\n--- Bus: {bus_id} ({bus_label}, degree={degrees[bus_id]}) ---")
        for h in hop_range:
            gc.collect()

            # Step 2: BFS scoping
            t_scope = time.perf_counter()
            scoped = bfs_scoped_branches(n, bus_id, h, branch_idx)
            scope_elapsed = time.perf_counter() - t_scope

            k = len(scoped)
            n1_count = k
            n2_count = k * (k - 1) // 2
            n3_count = k * (k - 1) * (k - 2) // 6

            print(
                f"\n  h={h}: {k} scoped branches → "
                f"N-1={n1_count}, N-2={n2_count:,}, N-3={n3_count:,}"
            )

            sweep_result: dict = {
                "h": h,
                "scoped_branches": k,
                "n1_combinations": n1_count,
                "n2_combinations": n2_count,
                "n3_combinations": n3_count,
                "scope_us": scope_elapsed * 1e6,
            }

            # N-1 sweep
            t0 = time.perf_counter()
            _, n1_violations = sweep_n1(BODF, p0, s_nom, scoped)
            n1_elapsed = time.perf_counter() - t0
            sweep_result["n1_ms"] = n1_elapsed * 1000
            sweep_result["n1_violations"] = n1_violations
            print(f"    N-1: {n1_elapsed * 1000:.3f} ms, {n1_violations} violations")

            # N-2 sweep
            if n2_count <= 500_000:
                t0 = time.perf_counter()
                _, n2_violations = sweep_n2(BODF, p0, s_nom, scoped)
                n2_elapsed = time.perf_counter() - t0
                sweep_result["n2_ms"] = n2_elapsed * 1000
                sweep_result["n2_violations"] = n2_violations
                print(
                    f"    N-2: {n2_elapsed * 1000:.3f} ms ({n2_count:,} combos), "
                    f"{n2_violations} violations"
                )
            else:
                sweep_result["n2_ms"] = None
                sweep_result["n2_note"] = f"Skipped: {n2_count:,} combos exceeds 500k limit"
                print(f"    N-2: SKIPPED ({n2_count:,} combos)")

            # N-3 sweep
            max_n3 = 50_000
            if n3_count <= max_n3:
                t0 = time.perf_counter()
                n3_actual, n3_violations = sweep_n3(BODF, p0, s_nom, scoped)
                n3_elapsed = time.perf_counter() - t0
                sweep_result["n3_ms"] = n3_elapsed * 1000
                sweep_result["n3_violations"] = n3_violations
                sweep_result["n3_actual"] = n3_actual
                print(
                    f"    N-3: {n3_elapsed * 1000:.3f} ms ({n3_actual:,} combos), "
                    f"{n3_violations} violations"
                )
            elif n3_count <= 500_000:
                # Run capped
                t0 = time.perf_counter()
                n3_actual, n3_violations = sweep_n3(BODF, p0, s_nom, scoped, max_combos=max_n3)
                n3_elapsed = time.perf_counter() - t0
                sweep_result["n3_ms"] = n3_elapsed * 1000
                sweep_result["n3_violations"] = n3_violations
                sweep_result["n3_actual"] = n3_actual
                sweep_result["n3_capped"] = True
                print(
                    f"    N-3: {n3_elapsed * 1000:.3f} ms ({n3_actual:,}/{n3_count:,} combos, capped), "
                    f"{n3_violations} violations"
                )
            else:
                sweep_result["n3_ms"] = None
                sweep_result["n3_note"] = f"Skipped: {n3_count:,} combos exceeds limit"
                print(f"    N-3: SKIPPED ({n3_count:,} combos)")

            # Total user-perceived latency (scope + all sweeps)
            total_ms = sweep_result["scope_us"] / 1000 + sweep_result["n1_ms"]
            if sweep_result.get("n2_ms") is not None:
                total_ms += sweep_result["n2_ms"]
            if sweep_result.get("n3_ms") is not None:
                total_ms += sweep_result["n3_ms"]
            sweep_result["total_ms"] = total_ms
            print(f"    TOTAL user latency: {total_ms:.1f} ms")

            result["sweeps"][f"{bus_label}_h{h}"] = sweep_result

    return result


def main():
    all_results = {}

    for label, path in NETWORKS.items():
        hop_range = [1, 2, 3, 4]
        all_results[label] = run_sweep(label, path, hop_range)

    # Summary table
    print("\n" + "=" * 60)
    print("SUMMARY: Total user-perceived latency (ms)")
    print("=" * 60)
    print(
        f"{'Network':<12} {'Bus':<14} {'h':>2} {'Branches':>9} "
        f"{'N-1':>8} {'N-2':>10} {'N-3':>12} {'Total':>10}"
    )
    print("-" * 80)

    for label, data in all_results.items():
        for key, sweep in data["sweeps"].items():
            bus_type = "max-deg" if "max_degree" in key else "median"
            n1_str = f"{sweep['n1_ms']:.1f}ms"
            n2_str = f"{sweep['n2_ms']:.1f}ms" if sweep.get("n2_ms") is not None else "skip"
            n3_str = f"{sweep['n3_ms']:.1f}ms" if sweep.get("n3_ms") is not None else "skip"
            total_str = f"{sweep['total_ms']:.1f}ms"
            print(
                f"{label:<12} {bus_type:<14} {sweep['h']:>2} {sweep['scoped_branches']:>9} "
                f"{n1_str:>8} {n2_str:>10} {n3_str:>12} {total_str:>10}"
            )

    output_path = Path(__file__).parent / "sweep_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults written to {output_path}")

    return all_results


if __name__ == "__main__":
    main()
