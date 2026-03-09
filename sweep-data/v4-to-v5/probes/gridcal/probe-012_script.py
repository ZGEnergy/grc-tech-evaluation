"""Probe-012: Verify PTDF vs DCPF divergence claim on ACTIVSg10k.

Investigates whether the 743 MW max divergence between LinearAnalysis flows
and DCPF flows is real, and diagnoses the root cause (islands, transformer
taps, slack bus treatment, or computational error).
"""

from __future__ import annotations

import importlib.metadata
import time
from pathlib import Path

import numpy as np

DATA_DIR = Path("/workspace/data/networks")
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def main():
    print("=" * 70)
    print("Probe-012: PTDF vs DCPF divergence on ACTIVSg10k")
    print("=" * 70)

    import VeraGridEngine as vge
    from VeraGridEngine.enumerations import SolverType

    ver = importlib.metadata.version("veragridengine")
    print(f"GridCal (veragridengine) version: {ver}")

    # ── Load network ──
    grid = vge.open_file(NETWORK_FILE)
    n_bus = grid.get_bus_number()
    branches = list(grid.lines) + list(grid.transformers2w)
    n_branch = len(branches)
    n_lines = len(list(grid.lines))
    n_xfmrs = len(list(grid.transformers2w))
    print(f"Network: {n_bus} buses, {n_branch} branches")
    print(f"  Lines: {n_lines}, Transformers2W: {n_xfmrs}")

    # ── Island detection ──
    nc = vge.compile_numerical_circuit_at(grid)
    islands = nc.split_into_islands()
    n_islands = len(islands)
    print(f"\nIsland analysis: {n_islands} island(s)")
    for i, isl in enumerate(islands):
        print(f"  Island {i}: {isl.nbus} buses, {isl.nbr} branches")

    # ── Step 1: DCPF ──
    print("\n--- DCPF solve ---")
    pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
    t0 = time.perf_counter()
    pf_results = vge.power_flow(grid, options=pf_opts)
    t_dcpf = time.perf_counter() - t0
    print(f"DCPF converged: {pf_results.converged}")
    print(f"DCPF wall clock: {t_dcpf:.3f}s")

    dcpf_flows = pf_results.Sf.real
    sbus = pf_results.Sbus.real
    print(f"DCPF flows shape: {dcpf_flows.shape}")
    print(f"DCPF flows range: [{dcpf_flows.min():.3f}, {dcpf_flows.max():.3f}]")
    print(f"Sbus shape: {sbus.shape}, sum: {sbus.sum():.6f}")

    # ── Step 2: LinearAnalysis (PTDF) ──
    print("\n--- LinearAnalysis ---")
    t0 = time.perf_counter()
    la_results = vge.linear_power_flow(grid)
    t_ptdf = time.perf_counter() - t0
    print(f"PTDF compute time: {t_ptdf:.3f}s")

    ptdf = la_results.PTDF
    print(f"PTDF shape: {ptdf.shape}")
    print(f"PTDF range: [{ptdf.min():.6f}, {ptdf.max():.6f}]")

    # ── Step 3: Compare LA direct flows vs DCPF ──
    la_flows = None
    if hasattr(la_results, "Sf") and la_results.Sf is not None:
        la_flows = la_results.Sf.real

    if la_flows is not None:
        la_diff = np.abs(la_flows - dcpf_flows)
        print("\n--- LA direct flows vs DCPF ---")
        print(f"Max abs diff: {la_diff.max():.4f} MW")
        print(f"Mean abs diff: {la_diff.mean():.4f} MW")
        print(f"Median abs diff: {np.median(la_diff):.4f} MW")
        print(f"90th pctile: {np.percentile(la_diff, 90):.4f} MW")
        print(f"99th pctile: {np.percentile(la_diff, 99):.4f} MW")
        print(f"Branches with diff > 1 MW: {(la_diff > 1.0).sum()}")
        print(f"Branches with diff > 10 MW: {(la_diff > 10.0).sum()}")
        print(f"Branches with diff > 100 MW: {(la_diff > 100.0).sum()}")

        worst_indices = np.argsort(la_diff)[-10:][::-1]
        print("\nTop 10 worst branches (LA vs DCPF):")
        for idx in worst_indices:
            br = branches[idx]
            br_type = "Line" if idx < n_lines else "Xfmr"
            print(
                f"  [{idx}] {br_type} '{br.name}': LA={la_flows[idx]:.3f}, "
                f"DCPF={dcpf_flows[idx]:.3f}, diff={la_diff[idx]:.3f}"
            )

        # Split by branch type
        line_diffs = la_diff[:n_lines]
        xfmr_diffs = la_diff[n_lines:]
        print("\n--- Divergence by branch type (LA vs DCPF) ---")
        print(
            f"Lines ({n_lines}):        max={line_diffs.max():.4f}, mean={line_diffs.mean():.4f}"
        )
        print(
            f"Transformers ({n_xfmrs}): max={xfmr_diffs.max():.4f}, mean={xfmr_diffs.mean():.4f}"
        )
    else:
        la_diff = None
        print("LA direct flows NOT available")

    # ── Step 4: PTDF @ Sbus vs DCPF ──
    ptdf_predicted = ptdf @ sbus
    ptdf_diff = np.abs(ptdf_predicted - dcpf_flows)
    print("\n--- PTDF @ Sbus vs DCPF ---")
    print(f"Max abs diff: {ptdf_diff.max():.4f} MW")
    print(f"Mean abs diff: {ptdf_diff.mean():.4f} MW")
    print(f"Branches with diff > 100 MW: {(ptdf_diff > 100.0).sum()}")

    # ── Step 5: Transformer tap analysis ──
    print("\n--- Transformer tap analysis ---")
    taps = []
    for t in grid.transformers2w:
        taps.append(t.tap_module if hasattr(t, "tap_module") else None)
    taps_arr = np.array([t for t in taps if t is not None])
    if len(taps_arr) > 0:
        non_unity = np.abs(taps_arr - 1.0) > 1e-6
        print(f"Non-unity tap transformers: {non_unity.sum()} / {len(taps_arr)}")
        print(f"Tap ratio range: [{taps_arr.min():.6f}, {taps_arr.max():.6f}]")

        if la_diff is not None and len(taps_arr) == n_xfmrs:
            tap_dev = np.abs(taps_arr - 1.0)
            xfmr_err = la_diff[n_lines:]
            if non_unity.sum() > 2:
                corr = np.corrcoef(tap_dev[non_unity], xfmr_err[non_unity])[0, 1]
                print(f"Correlation (tap deviation vs xfmr error): {corr:.4f}")

    # ── Step 6: Slack bus ──
    print("\n--- Slack bus analysis ---")
    slack_buses = [(i, bus.name) for i, bus in enumerate(grid.buses) if bus.is_slack]
    print(f"Slack buses: {len(slack_buses)}")
    for idx, name in slack_buses[:5]:
        print(f"  Bus {idx}: '{name}'")

    col_sums = np.abs(ptdf).sum(axis=0)
    min_col_idx = int(np.argmin(col_sums))
    print(f"PTDF near-zero column: bus {min_col_idx} (sum={col_sums[min_col_idx]:.8f})")

    # Try slack correction
    if slack_buses:
        slack_idx = slack_buses[0][0]
        sbus_corr = sbus.copy()
        slack_power = sbus_corr[slack_idx]
        print(f"Slack bus injection: {slack_power:.4f} MW")
        sbus_corr[slack_idx] = 0.0
        ptdf_corr = ptdf @ sbus_corr
        corr_diff = np.abs(ptdf_corr - dcpf_flows)
        print("After zeroing slack injection:")
        print(f"  Max abs diff: {corr_diff.max():.4f} MW")
        print(f"  Mean abs diff: {corr_diff.mean():.4f} MW")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if la_diff is not None:
        print(f"LA vs DCPF max diff:   {la_diff.max():.4f} MW  (claim: ~743 MW)")
    print(f"PTDF@Sbus vs DCPF max: {ptdf_diff.max():.4f} MW  (claim: ~15139 MW)")
    print(f"Islands: {n_islands}")
    if len(taps_arr) > 0:
        print(f"Non-unity taps: {non_unity.sum()}")


if __name__ == "__main__":
    t_start = time.perf_counter()
    main()
    t_total = time.perf_counter() - t_start
    print(f"\nTotal probe wall clock: {t_total:.2f}s")
