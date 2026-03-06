"""C-9: PTDF Matrix Computation on MEDIUM (10k-bus)."""

import time
import tracemalloc

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
    # Fix zero-impedance branches that cause singular B matrix
    n.lines.loc[n.lines.x == 0, "x"] = 0.0001
    n.transformers.loc[n.transformers.x == 0, "x"] = 0.0001
    return n


def main():
    print("=" * 70)
    print("C-9: PTDF Matrix Computation on MEDIUM (10k-bus)")
    print("=" * 70)

    n = load_network(MEDIUM)
    print(
        f"Network: {len(n.buses)} buses, {len(n.lines)} lines, {len(n.transformers)} transformers"
    )

    # Must determine network topology first
    print("\nDetermining network topology...")
    n.determine_network_topology()

    # Get sub-networks
    sub_networks = n.sub_networks.index.tolist()
    print(f"Sub-networks found: {len(sub_networks)}")
    for sn_name in sub_networks:
        sn_buses = n.buses[n.buses.sub_network == sn_name]
        sn_lines = n.lines[n.lines.bus0.isin(sn_buses.index) & n.lines.bus1.isin(sn_buses.index)]
        print(f"  {sn_name}: {len(sn_buses)} buses, {len(sn_lines)} lines")

    # Compute PTDF for the largest sub-network
    largest_sn = sub_networks[0]  # typically the main interconnected network
    if len(sub_networks) > 1:
        sn_sizes = {}
        for sn_name in sub_networks:
            sn_buses = n.buses[n.buses.sub_network == sn_name]
            sn_sizes[sn_name] = len(sn_buses)
        largest_sn = max(sn_sizes, key=sn_sizes.get)
        print(f"\nUsing largest sub-network: {largest_sn} ({sn_sizes[largest_sn]} buses)")

    sub_network = n.sub_networks.obj[largest_sn]

    print("\nComputing PTDF matrix...")
    tracemalloc.start()
    t0 = time.perf_counter()
    sub_network.calculate_PTDF()
    wall_clock = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1024 / 1024

    ptdf = sub_network.PTDF
    rows, cols = ptdf.shape
    total_elements = rows * cols
    nonzero = np.count_nonzero(ptdf)
    density = nonzero / total_elements if total_elements > 0 else 0

    print(f"\nPTDF matrix dimensions: {rows} x {cols}")
    print(f"Total elements: {total_elements:,}")
    print(f"Non-zero elements: {nonzero:,}")
    print(f"Density: {density:.4f} ({density * 100:.2f}%)")
    print(f"Memory for matrix: {ptdf.nbytes / 1024 / 1024:.2f} MB")
    print(f"\nWall-clock: {wall_clock:.4f}s")
    print(f"Peak memory (tracemalloc): {peak_mb:.2f} MB")

    # Sanity check: each column should sum to ~0 (PTDF property)
    col_sums = ptdf.sum(axis=0)
    print(f"\nColumn sum range: [{col_sums.min():.6f}, {col_sums.max():.6f}]")
    print(f"Max abs column sum: {np.abs(col_sums).max():.6f}")

    # Value range
    print(f"PTDF value range: [{ptdf.min():.6f}, {ptdf.max():.6f}]")

    print("\n--- RESULTS ---")
    print(f"wall_clock_s={wall_clock:.4f}")
    print(f"peak_memory_mb={peak_mb:.2f}")
    print(f"matrix_rows={rows}")
    print(f"matrix_cols={cols}")
    print(f"density={density:.6f}")
    print(f"matrix_memory_mb={ptdf.nbytes / 1024 / 1024:.2f}")


if __name__ == "__main__":
    main()
