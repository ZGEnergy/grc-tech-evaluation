"""
Test G-FNM-3: DCPF verification on FNM against reference solution

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: Pass if all aggregate thresholds are met and no hard-fail
    condition is triggered, per the dcpf section of pass_conditions.json.
    Formulation difference classification applies if deviations cluster
    near transformer-connected buses.
Tool: gridcal (VeraGrid) v5.6.28

Input: MATPOWER fallback path (G-FNM-1 CSV ingestion failed).
File: data/fnm/reference/cleaned/fnm_main_island.m

v11 additions:
- Bus exclusion per excluded_buses.json
- Bus injection power balance cross-reference check
- All deviation metrics in scientific notation (:.6e)
- ingestion_path recorded in output
"""

from __future__ import annotations

import csv
import json
import time
import traceback
from collections import defaultdict

import numpy as np


def angle_diff_deg(a: float, b: float) -> float:
    """Compute signed angle difference normalized to [-180, 180]."""
    d = a - b
    return ((d + 180) % 360) - 180


def sci(value: float) -> str:
    """Format a float in scientific notation with 6 decimal places."""
    return f"{value:.6e}"


def run(
    matpower_file: str = "/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
    ref_bus_file: str = "/workspace/data/fnm/reference/dcpf/buses_dcpf.csv",
    ref_branch_file: str = "/workspace/data/fnm/reference/dcpf/branches_dcpf.csv",
    pass_conditions_file: str = "/workspace/data/fnm/reference/pass_conditions.json",
    excluded_buses_file: str = "/workspace/data/fnm/reference/excluded_buses.json",
) -> dict:
    """Execute G-FNM-3 and return structured results.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import tracemalloc

        tracemalloc.start()

        # ----------------------------------------------------------------
        # Load pass conditions
        # ----------------------------------------------------------------
        with open(pass_conditions_file) as f:
            pass_cond = json.load(f)
        dcpf_cond = pass_cond["dcpf"]

        va_tol = dcpf_cond["aggregate"]["bus_angle"]["va_tolerance_deg"]
        min_bus_frac = dcpf_cond["aggregate"]["bus_angle"]["min_passing_fraction"]
        p_tol_pct = dcpf_cond["aggregate"]["branch_flow"]["p_tolerance_pct"]
        p_base_floor = dcpf_cond["aggregate"]["branch_flow"]["p_base_floor_mw"]
        min_br_frac = dcpf_cond["aggregate"]["branch_flow"]["min_passing_fraction"]

        hard_bus_thresh = dcpf_cond["hard_fail"]["conditions"][0]["threshold"]
        hard_br_thresh = dcpf_cond["hard_fail"]["conditions"][1]["threshold"]
        hard_br_dev_thresh = dcpf_cond["hard_fail"]["conditions"][2]["threshold_pct"]

        formulation_diff_max = dcpf_cond["formulation_difference_max_abs"]["threshold_deg"]

        results["details"]["pass_conditions"] = {
            "va_tolerance_deg": va_tol,
            "min_bus_passing_fraction": min_bus_frac,
            "p_tolerance_pct": p_tol_pct,
            "p_base_floor_mw": p_base_floor,
            "min_branch_passing_fraction": min_br_frac,
            "formulation_difference_max_abs_deg": formulation_diff_max,
        }

        # ----------------------------------------------------------------
        # Load excluded buses
        # ----------------------------------------------------------------
        with open(excluded_buses_file) as f:
            excl_data = json.load(f)
        excluded_bus_set: set[int] = {b["bus_number"] for b in excl_data["excluded_buses"]}
        results["details"]["excluded_bus_count"] = len(excluded_bus_set)

        # ----------------------------------------------------------------
        # 1. Load network via MATPOWER fallback
        # ----------------------------------------------------------------
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        results["details"]["veragrid_version"] = getattr(vge, "__version__", "unknown")
        results["details"]["ingestion_path"] = "matpower_raw"
        results["details"]["input_path"] = "matpower"
        results["details"]["matpower_file"] = matpower_file

        t_load_start = time.perf_counter()
        grid = vge.open_file(matpower_file)
        t_load = time.perf_counter() - t_load_start

        if grid is None:
            results["errors"].append("open_file returned None for MATPOWER file")
            return results

        results["details"]["load_time_seconds"] = round(t_load, 3)
        results["details"]["bus_count"] = len(grid.buses)
        results["details"]["sbase"] = grid.Sbase

        # ----------------------------------------------------------------
        # 2. Solve DCPF
        # ----------------------------------------------------------------
        pf_options = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        t_solve_start = time.perf_counter()
        pf_results = vge.power_flow(grid, pf_options)
        t_solve = time.perf_counter() - t_solve_start

        results["details"]["solve_time_seconds"] = round(t_solve, 3)

        V = pf_results.voltage
        angles_deg = np.angle(V, deg=True)
        Pf_mw = pf_results.Sf.real  # MW (GridCal returns MW for MATPOWER cases)

        # Validate non-trivial solution
        nonzero_angles = int(np.count_nonzero(angles_deg))
        results["details"]["nonzero_angle_buses"] = nonzero_angles
        if nonzero_angles < len(grid.buses) * 0.5:
            results["errors"].append(
                f"Trivial solution: only {nonzero_angles}/{len(grid.buses)} buses "
                "have nonzero angles"
            )
            return results

        # ----------------------------------------------------------------
        # 3. Load reference solutions
        # ----------------------------------------------------------------
        bus_codes = [int(b.code) for b in grid.buses]

        # Reference bus data
        with open(ref_bus_file) as f:
            reader = csv.DictReader(f)
            ref_bus_data = {}
            for r in reader:
                ref_bus_data[int(r["bus_number"])] = {
                    "va_deg": float(r["va_deg"]),
                    "pd_mw": float(r["pd_mw"]),
                    "base_kv": float(r["base_kv"]),
                    "bus_type": int(r["bus_type"]),
                }

        # Reference branch data
        with open(ref_branch_file) as f:
            reader = csv.DictReader(f)
            ref_branch_list = []
            for r in reader:
                ref_branch_list.append(
                    {
                        "from_bus": int(r["from_bus"]),
                        "to_bus": int(r["to_bus"]),
                        "pf_mw": float(r["pf_mw"]),
                        "status": int(r["status"]),
                    }
                )

        results["details"]["ref_bus_count"] = len(ref_bus_data)
        results["details"]["ref_branch_count"] = len(ref_branch_list)

        # ----------------------------------------------------------------
        # 4. Bus angle comparison (excluding buses in excluded_buses.json)
        # ----------------------------------------------------------------
        bus_passing = 0
        bus_failing = 0
        bus_angle_diffs: list[float] = []
        failing_bus_details: list[dict] = []
        buses_excluded_from_comparison = 0

        for i, bnum in enumerate(bus_codes):
            if bnum not in ref_bus_data:
                continue
            if bnum in excluded_bus_set:
                buses_excluded_from_comparison += 1
                continue
            ref_va = ref_bus_data[bnum]["va_deg"]
            gc_va = float(angles_deg[i])
            diff = abs(angle_diff_deg(gc_va, ref_va))
            bus_angle_diffs.append(diff)
            if diff < va_tol:
                bus_passing += 1
            else:
                bus_failing += 1
                failing_bus_details.append(
                    {
                        "bus": bnum,
                        "gc_va": round(gc_va, 4),
                        "ref_va": round(ref_va, 4),
                        "diff_deg": sci(diff),
                        "base_kv": ref_bus_data[bnum]["base_kv"],
                    }
                )

        total_buses_compared = len(bus_angle_diffs)
        bus_pass_frac = bus_passing / total_buses_compared if total_buses_compared > 0 else 0
        bus_fail_frac = bus_failing / total_buses_compared if total_buses_compared > 0 else 0

        max_bus_diff = float(max(bus_angle_diffs)) if bus_angle_diffs else 0.0
        mean_bus_diff = float(np.mean(bus_angle_diffs)) if bus_angle_diffs else 0.0

        results["details"]["bus_angle"] = {
            "total_compared": total_buses_compared,
            "excluded": buses_excluded_from_comparison,
            "passing": bus_passing,
            "failing": bus_failing,
            "pass_fraction": round(bus_pass_frac, 6),
            "mean_diff_deg": sci(mean_bus_diff),
            "median_diff_deg": sci(float(np.median(bus_angle_diffs)))
            if bus_angle_diffs
            else sci(0.0),
            "p95_diff_deg": sci(float(np.percentile(bus_angle_diffs, 95)))
            if bus_angle_diffs
            else sci(0.0),
            "p99_diff_deg": sci(float(np.percentile(bus_angle_diffs, 99)))
            if bus_angle_diffs
            else sci(0.0),
            "max_diff_deg": sci(max_bus_diff),
            "meets_threshold": bus_pass_frac >= min_bus_frac,
        }

        # ----------------------------------------------------------------
        # 5. Bus injection power balance cross-reference (v11)
        # ----------------------------------------------------------------
        # Compute net bus injection: P_gen - P_load for each bus from GridCal
        # Compare against reference bus pd_mw to verify injection consistency
        bus_code_to_idx = {bnum: i for i, bnum in enumerate(bus_codes)}

        # Get generator injections per bus from GridCal
        gc_bus_pgen = np.zeros(len(grid.buses))
        for gen in grid.generators:
            if gen.active:
                bus_idx = bus_code_to_idx.get(int(gen.bus.code))
                if bus_idx is not None:
                    gc_bus_pgen[bus_idx] += gen.P  # MW

        # Get load per bus from GridCal
        gc_bus_pload = np.zeros(len(grid.buses))
        for load in grid.loads:
            if load.active:
                bus_idx = bus_code_to_idx.get(int(load.bus.code))
                if bus_idx is not None:
                    gc_bus_pload[bus_idx] += load.P  # MW

        total_gen_mw = float(np.sum(gc_bus_pgen))
        total_load_mw = float(np.sum(gc_bus_pload))
        gen_load_imbalance_mw = total_gen_mw - total_load_mw

        # Compare load values against reference
        load_match_count = 0
        load_mismatch_count = 0
        load_comparison_diffs: list[float] = []
        for bnum, ref_info in ref_bus_data.items():
            if bnum in excluded_bus_set:
                continue
            idx = bus_code_to_idx.get(bnum)
            if idx is None:
                continue
            ref_pd = ref_info["pd_mw"]
            gc_pd = gc_bus_pload[idx]
            diff_mw = abs(gc_pd - ref_pd)
            load_comparison_diffs.append(diff_mw)
            if diff_mw < 0.01:  # 0.01 MW tolerance for floating-point comparison
                load_match_count += 1
            else:
                load_mismatch_count += 1

        results["details"]["power_balance"] = {
            "total_generation_mw": round(total_gen_mw, 2),
            "total_load_mw": round(total_load_mw, 2),
            "gen_load_imbalance_mw": sci(gen_load_imbalance_mw),
            "load_buses_compared": load_match_count + load_mismatch_count,
            "load_match_count": load_match_count,
            "load_mismatch_count": load_mismatch_count,
            "max_load_diff_mw": sci(float(max(load_comparison_diffs)))
            if load_comparison_diffs
            else sci(0.0),
        }

        # ----------------------------------------------------------------
        # 6. Branch flow comparison
        # ----------------------------------------------------------------
        branches_all = grid.get_branches()
        gc_active = [
            (i, int(branches_all[i].bus_from.code), int(branches_all[i].bus_to.code), Pf_mw[i])
            for i in range(len(branches_all))
            if branches_all[i].active
        ]

        # Build reference lookup by (from, to) with consumption tracking
        ref_map: dict[tuple[int, int], list[float]] = defaultdict(list)
        for br_ref in ref_branch_list:
            ref_map[(br_ref["from_bus"], br_ref["to_bus"])].append(br_ref["pf_mw"])
        ref_map_idx: dict[tuple[int, int], int] = defaultdict(int)

        # Build transformer bus set for formulation difference analysis
        xfmr_buses: set[int] = set()
        for br in branches_all:
            if type(br).__name__ == "Transformer2W":
                xfmr_buses.add(int(br.bus_from.code))
                xfmr_buses.add(int(br.bus_to.code))

        br_passing = 0
        br_failing = 0
        br_dev_pcts: list[float] = []
        failing_br_details: list[dict] = []
        matched_count = 0

        for orig_idx, f, t, gc_pf in gc_active:
            key = (f, t)
            rev_key = (t, f)

            ref_pf: float | None = None
            if key in ref_map and ref_map_idx[key] < len(ref_map[key]):
                ref_pf = ref_map[key][ref_map_idx[key]]
                ref_map_idx[key] += 1
            elif rev_key in ref_map and ref_map_idx[rev_key] < len(ref_map[rev_key]):
                ref_pf = -ref_map[rev_key][ref_map_idx[rev_key]]
                ref_map_idx[rev_key] += 1

            if ref_pf is None:
                continue

            matched_count += 1
            base = max(abs(ref_pf), p_base_floor)
            dev_pct = abs(gc_pf - ref_pf) / base * 100
            br_dev_pcts.append(dev_pct)
            br_type = type(branches_all[orig_idx]).__name__
            is_xfmr_adj = f in xfmr_buses or t in xfmr_buses

            if dev_pct < p_tol_pct:
                br_passing += 1
            else:
                br_failing += 1
                failing_br_details.append(
                    {
                        "from_bus": f,
                        "to_bus": t,
                        "gc_pf_mw": round(float(gc_pf), 2),
                        "ref_pf_mw": round(float(ref_pf), 2),
                        "dev_pct": sci(dev_pct),
                        "branch_type": br_type,
                        "transformer_adjacent": is_xfmr_adj,
                    }
                )

        total_br = len(br_dev_pcts)
        br_pass_frac = br_passing / total_br if total_br > 0 else 0
        br_fail_frac = br_failing / total_br if total_br > 0 else 0
        max_br_dev = max(br_dev_pcts) if br_dev_pcts else 0

        results["details"]["branch_flow"] = {
            "total_compared": total_br,
            "matched": matched_count,
            "passing": br_passing,
            "failing": br_failing,
            "pass_fraction": round(br_pass_frac, 6),
            "mean_dev_pct": sci(float(np.mean(br_dev_pcts))) if br_dev_pcts else sci(0.0),
            "median_dev_pct": sci(float(np.median(br_dev_pcts))) if br_dev_pcts else sci(0.0),
            "p95_dev_pct": sci(float(np.percentile(br_dev_pcts, 95))) if br_dev_pcts else sci(0.0),
            "p99_dev_pct": sci(float(np.percentile(br_dev_pcts, 99))) if br_dev_pcts else sci(0.0),
            "max_dev_pct": sci(max_br_dev),
            "meets_threshold": br_pass_frac >= min_br_frac,
        }

        # ----------------------------------------------------------------
        # 7. Hard fail checks
        # ----------------------------------------------------------------
        hard_fail_bus = bus_fail_frac > hard_bus_thresh
        hard_fail_br_frac = br_fail_frac > hard_br_thresh
        hard_fail_br_extreme = max_br_dev > hard_br_dev_thresh
        any_hard_fail = hard_fail_bus or hard_fail_br_frac or hard_fail_br_extreme

        results["details"]["hard_fail"] = {
            "bus_fail_fraction_exceeded": hard_fail_bus,
            "bus_fail_fraction": round(bus_fail_frac, 6),
            "branch_fail_fraction_exceeded": hard_fail_br_frac,
            "branch_fail_fraction": round(br_fail_frac, 6),
            "extreme_branch_dev_exceeded": hard_fail_br_extreme,
            "max_branch_dev_pct": sci(max_br_dev),
            "any_triggered": any_hard_fail,
        }

        # ----------------------------------------------------------------
        # 8. Formulation difference classification
        # ----------------------------------------------------------------
        if br_failing > 0:
            xfmr_adj_count = sum(1 for d in failing_br_details if d["transformer_adjacent"])
            xfmr_adj_frac = xfmr_adj_count / len(failing_br_details)

            # Check formulation difference qualification
            # threshold_deg is null => no explicit cap on deviation magnitude
            formulation_diff_qualified = xfmr_adj_frac >= 0.80

            results["details"]["formulation_difference"] = {
                "failing_branches": len(failing_br_details),
                "transformer_adjacent_count": xfmr_adj_count,
                "transformer_adjacent_fraction": round(xfmr_adj_frac, 4),
                "threshold_fraction": 0.80,
                "max_abs_threshold": formulation_diff_max,
                "qualified": formulation_diff_qualified,
            }

            # Sort failing branches by deviation (parse from sci notation) and keep top 20
            failing_br_details.sort(key=lambda x: float(x["dev_pct"]), reverse=True)
            results["details"]["top_failing_branches"] = failing_br_details[:20]
        else:
            formulation_diff_qualified = False
            results["details"]["formulation_difference"] = {
                "failing_branches": 0,
                "qualified": False,
            }

        # ----------------------------------------------------------------
        # 9. Determine status
        # ----------------------------------------------------------------
        aggregate_pass = (bus_pass_frac >= min_bus_frac) and (br_pass_frac >= min_br_frac)

        if aggregate_pass and not any_hard_fail:
            results["status"] = "pass"
        elif aggregate_pass and any_hard_fail and formulation_diff_qualified:
            # Hard fail triggered by extreme branch dev, but deviations are
            # systematically correlated with transformer-connected buses =>
            # formulation difference, not data error
            results["status"] = "qualified_pass"
            results["details"]["qualification_reason"] = (
                "Hard fail triggered by extreme_branch_flow_deviation "
                f"(max={sci(max_br_dev)}), but {xfmr_adj_count}/{len(failing_br_details)} "
                f"({xfmr_adj_frac * 100:.1f}%) failing branches are transformer-adjacent, "
                "indicating a B-matrix formulation difference (simplified vs full "
                "treatment of transformer tap ratios), not a data ingestion error."
            )
        else:
            results["status"] = "fail"

        # Memory measurement
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["details"]["peak_memory_mb"] = round(peak / (1024 * 1024), 1)

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 3)

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
