"""
Probe-001: Verify G-FNM-3 claim that PyPSA achieves 0.0 mean and max deviation
(both bus angles and branch flows) across all 27,862 buses and 32,532 branches
in G-FNM-3 DCPF on the ACTIVSg70k (FNM) network.

This is an independent re-execution of the test using the same shared matpower_loader
that the original test used. Deviations are reported at full float64 precision.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

# Add shared loader to path (same as original test)
sys.path.insert(0, "/workspace/evaluations/shared")

CLEANED_M = Path("/workspace/data/fnm/reference/cleaned/fnm_main_island.m")
REF_BUSES = Path("/workspace/data/fnm/reference/dcpf/buses_dcpf.csv")
REF_BRANCHES = Path("/workspace/data/fnm/reference/dcpf/branches_dcpf.csv")
PASS_CONDITIONS = Path("/workspace/data/fnm/reference/pass_conditions.json")
EXCLUDED_BUSES = Path("/workspace/data/fnm/reference/excluded_buses.json")


def main() -> None:
    import json

    import pandas as pd
    import pypsa
    from matpower_loader import load_pypsa
    from matpowercaseframes import CaseFrames

    print(f"PyPSA version: {pypsa.__version__}")
    print(f"NumPy version: {np.__version__}")
    print(f"Pandas version: {pd.__version__}")
    print()

    # Load pass conditions
    with open(PASS_CONDITIONS) as f:
        pass_conds = json.load(f)
    dcpf_conds = pass_conds["dcpf"]
    P_BASE_FLOOR = dcpf_conds["aggregate"]["branch_flow"]["p_base_floor_mw"]

    # Load excluded buses
    with open(EXCLUDED_BUSES) as f:
        excl_data = json.load(f)
    excluded_bus_set = {
        int(b["bus_number"]) for b in excl_data.get("excluded_buses", [])
    }
    print(f"Excluded buses: {len(excluded_bus_set)}")

    # Load reference data
    ref_buses_df = pd.read_csv(REF_BUSES)
    ref_branches_df = pd.read_csv(REF_BRANCHES)
    print(f"Reference buses: {len(ref_buses_df)}")
    print(f"Reference branches: {len(ref_branches_df)}")
    print()

    # Load MATPOWER case via shared loader (same as original test)
    print("Loading MATPOWER case via shared matpower_loader.load_pypsa()...")
    t0 = time.perf_counter()
    net = load_pypsa(str(CLEANED_M), overwrite_zero_s_nom=100000.0)
    net.set_snapshots([0])
    t_load = time.perf_counter() - t0
    print(f"  Load time: {t_load:.2f}s")
    print(f"  Buses: {len(net.buses)}")
    print(f"  Lines: {len(net.lines)}")
    print(f"  Transformers: {len(net.transformers)}")
    print(f"  Generators: {len(net.generators)}")

    # Also load raw CaseFrames for branch analysis
    cf = CaseFrames(str(CLEANED_M))
    bus_array = cf.bus.values
    branch_array = cf.branch.values
    branch_status = branch_array[:, 10].astype(int)
    n_active = int((branch_status == 1).sum())
    print(f"  MATPOWER total branches: {len(branch_array)}, active: {n_active}")
    print()

    # Run DCPF
    print("Running DCPF (net.lpf())...")
    t1 = time.perf_counter()
    net.lpf()
    t_solve = time.perf_counter() - t1
    print(f"  Solve time: {t_solve:.2f}s")
    print()

    # Extract results
    if (
        hasattr(net, "buses_t")
        and "v_ang" in net.buses_t
        and len(net.buses_t.v_ang) > 0
    ):
        pypsa_va_rad = net.buses_t.v_ang.iloc[0]
    else:
        pypsa_va_rad = net.buses.v_ang
    pypsa_va_deg_series = np.degrees(pypsa_va_rad)

    if hasattr(net, "lines_t") and "p0" in net.lines_t and len(net.lines_t.p0) > 0:
        pypsa_line_p0 = net.lines_t.p0.iloc[0]
    else:
        pypsa_line_p0 = net.lines.get("p0", pd.Series(dtype=float))

    if (
        hasattr(net, "transformers_t")
        and "p0" in net.transformers_t
        and len(net.transformers_t.p0) > 0
    ):
        pypsa_xfmr_p0 = net.transformers_t.p0.iloc[0]
    else:
        pypsa_xfmr_p0 = net.transformers.get("p0", pd.Series(dtype=float))

    # ── Bus voltage angle comparison ─────────────────────────────────────────
    print("=" * 70)
    print("BUS VOLTAGE ANGLE COMPARISON (float64 precision)")
    print("=" * 70)

    ref_bus_va = {
        int(row["bus_number"]): float(row["va_deg"])
        for _, row in ref_buses_df.iterrows()
    }

    va_deviations = []
    va_bus_numbers = []
    for bus_name in pypsa_va_deg_series.index:
        try:
            bus_num = int(bus_name)
        except (ValueError, TypeError):
            continue
        if bus_num in excluded_bus_set:
            continue
        if bus_num in ref_bus_va:
            dev = abs(float(pypsa_va_deg_series[bus_name]) - ref_bus_va[bus_num])
            va_deviations.append(dev)
            va_bus_numbers.append(bus_num)

    va_deviations = np.array(va_deviations, dtype=np.float64)
    n_buses_compared = len(va_deviations)

    print(f"Buses compared (non-excluded): {n_buses_compared}")
    print(f"  Max deviation (deg):  {np.max(va_deviations):.18e}")
    print(f"  Mean deviation (deg): {np.mean(va_deviations):.18e}")
    print(f"  Min deviation (deg):  {np.min(va_deviations):.18e}")
    print(f"  Std deviation (deg):  {np.std(va_deviations):.18e}")
    print(f"  P50 deviation (deg):  {np.median(va_deviations):.18e}")
    print(f"  P95 deviation (deg):  {np.percentile(va_deviations, 95):.18e}")
    print(f"  P99 deviation (deg):  {np.percentile(va_deviations, 99):.18e}")

    # Count buses exceeding various thresholds
    n_above_1e6 = int(np.sum(va_deviations > 1e-6))
    n_above_1e9 = int(np.sum(va_deviations > 1e-9))
    n_above_1e12 = int(np.sum(va_deviations > 1e-12))
    n_nonzero = int(np.sum(va_deviations > 0.0))
    print(f"  Buses with dev > 1e-6 deg:  {n_above_1e6}")
    print(f"  Buses with dev > 1e-9 deg:  {n_above_1e9}")
    print(f"  Buses with dev > 1e-12 deg: {n_above_1e12}")
    print(f"  Buses with dev > 0.0 (exact): {n_nonzero}")

    # Outlier buses (dev > 1e-6)
    if n_above_1e6 > 0:
        outlier_indices = np.where(va_deviations > 1e-6)[0]
        print(
            f"\n  Outlier buses (dev > 1e-6 deg): top {min(20, len(outlier_indices))}"
        )
        sorted_idx = outlier_indices[np.argsort(va_deviations[outlier_indices])[::-1]]
        for i in sorted_idx[:20]:
            print(f"    Bus {va_bus_numbers[i]}: dev = {va_deviations[i]:.18e} deg")
    else:
        print("  No outlier buses with dev > 1e-6 deg.")

    # Tally of nonzero deviation buses (any floating-point deviation)
    if n_nonzero > 0:
        nonzero_devs = va_deviations[va_deviations > 0.0]
        print(f"\n  Distribution of nonzero deviations ({len(nonzero_devs)} buses):")
        print(f"    Max: {nonzero_devs.max():.18e}")
        print(f"    Min: {nonzero_devs.min():.18e}")
        print(f"    Mean: {nonzero_devs.mean():.18e}")

    # ── Branch flow comparison ────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("BRANCH FLOW COMPARISON (float64 precision)")
    print("=" * 70)

    # Classify branches as line vs transformer (same logic as original test)
    bus_v_nom = dict(zip(bus_array[:, 0].astype(int), bus_array[:, 9]))
    n_branches_mat = branch_array.shape[0]
    is_xfmr = np.zeros(n_branches_mat, dtype=bool)
    for i in range(n_branches_mat):
        fbus = int(branch_array[i, 0])
        tbus = int(branch_array[i, 1])
        tap = branch_array[i, 8]
        shift = branch_array[i, 9]
        v0 = bus_v_nom.get(fbus, 0)
        v1 = bus_v_nom.get(tbus, 0)
        is_xfmr[i] = (v0 != v1) or (tap != 0.0 and tap != 1.0) or (shift != 0.0)

    line_counter = 0
    xfmr_counter = 0
    branch_pypsa_name = []
    for i in range(n_branches_mat):
        if is_xfmr[i]:
            branch_pypsa_name.append(("transformer", f"T{xfmr_counter}"))
            xfmr_counter += 1
        else:
            branch_pypsa_name.append(("line", f"L{line_counter}"))
            line_counter += 1

    line_p0_dict = dict(zip(pypsa_line_p0.index, pypsa_line_p0.values))
    xfmr_p0_dict = dict(zip(pypsa_xfmr_p0.index, pypsa_xfmr_p0.values))

    p_deviations_pct = []
    p_dev_lines = []
    p_dev_xfmrs = []
    p_abs_deviations = []
    active_row = 0

    for mat_row in range(n_branches_mat):
        if branch_status[mat_row] == 0:
            continue
        if active_row >= len(ref_branches_df):
            break

        comp_type, comp_name = branch_pypsa_name[mat_row]
        ref_p = float(ref_branches_df.iloc[active_row]["pf_mw"])

        if comp_type == "line":
            pypsa_p = line_p0_dict.get(comp_name, float("nan"))
        else:
            pypsa_p = xfmr_p0_dict.get(comp_name, float("nan"))

        if not np.isnan(pypsa_p):
            abs_dev = abs(float(pypsa_p) - ref_p)
            denom = max(abs(ref_p), P_BASE_FLOOR)
            dev_pct = (abs_dev / denom) * 100.0
            p_deviations_pct.append(dev_pct)
            p_abs_deviations.append(abs_dev)
            if comp_type == "line":
                p_dev_lines.append(dev_pct)
            else:
                p_dev_xfmrs.append(dev_pct)

        active_row += 1

    p_deviations_pct = np.array(p_deviations_pct, dtype=np.float64)
    p_abs_deviations = np.array(p_abs_deviations, dtype=np.float64)
    n_branches_compared = len(p_deviations_pct)

    print(f"Branches compared: {n_branches_compared}")
    print(f"  Max deviation (%):    {np.max(p_deviations_pct):.18e}")
    print(f"  Mean deviation (%):   {np.mean(p_deviations_pct):.18e}")
    print(f"  Min deviation (%):    {np.min(p_deviations_pct):.18e}")
    print(f"  P95 deviation (%):    {np.percentile(p_deviations_pct, 95):.18e}")
    print(f"  P99 deviation (%):    {np.percentile(p_deviations_pct, 99):.18e}")

    n_above_1e6 = int(np.sum(p_deviations_pct > 1e-6))
    n_above_1e9 = int(np.sum(p_deviations_pct > 1e-9))
    n_nonzero_br = int(np.sum(p_deviations_pct > 0.0))
    print(f"  Branches with dev > 1e-6 %:  {n_above_1e6}")
    print(f"  Branches with dev > 1e-9 %:  {n_above_1e9}")
    print(f"  Branches with dev > 0.0 (exact): {n_nonzero_br}")

    print(f"\n  Lines: {len(p_dev_lines)} compared")
    p_dev_lines_arr = np.array(p_dev_lines, dtype=np.float64)
    if len(p_dev_lines_arr) > 0:
        print(f"    Max dev (%): {np.max(p_dev_lines_arr):.18e}")
        print(f"    Mean dev (%): {np.mean(p_dev_lines_arr):.18e}")

    print(f"\n  Transformers: {len(p_dev_xfmrs)} compared")
    p_dev_xfmrs_arr = np.array(p_dev_xfmrs, dtype=np.float64)
    if len(p_dev_xfmrs_arr) > 0:
        print(f"    Max dev (%): {np.max(p_dev_xfmrs_arr):.18e}")
        print(f"    Mean dev (%): {np.mean(p_dev_xfmrs_arr):.18e}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    bus_max = float(np.max(va_deviations)) if len(va_deviations) > 0 else float("nan")
    bus_mean = float(np.mean(va_deviations)) if len(va_deviations) > 0 else float("nan")
    br_max = (
        float(np.max(p_deviations_pct)) if len(p_deviations_pct) > 0 else float("nan")
    )
    br_mean = (
        float(np.mean(p_deviations_pct)) if len(p_deviations_pct) > 0 else float("nan")
    )

    print(f"Bus angle max dev:    {bus_max:.18e} deg")
    print(f"Bus angle mean dev:   {bus_mean:.18e} deg")
    print(f"Branch flow max dev:  {br_max:.18e} %")
    print(f"Branch flow mean dev: {br_mean:.18e} %")
    print()

    # Assess claim
    CLAIM_EXACT_ZERO = (
        bus_max == 0.0 and bus_mean == 0.0 and br_max == 0.0 and br_mean == 0.0
    )
    print("Claim: 0.0 mean and max deviation across all buses and branches")
    print(f"Claim supported (exact float64 zero): {CLAIM_EXACT_ZERO}")

    # If not exact zero, check whether within display rounding (1e-6 threshold)
    CLAIM_ROUNDED_ZERO = bus_max < 1e-6 and br_max < 1e-6
    print(f"Claim supported (rounded to 0.0 at 6 decimal places): {CLAIM_ROUNDED_ZERO}")

    total_time = t_load + t_solve
    print(
        f"\nTotal wall clock: {total_time:.1f}s (load: {t_load:.1f}s, solve: {t_solve:.1f}s)"
    )


if __name__ == "__main__":
    main()
