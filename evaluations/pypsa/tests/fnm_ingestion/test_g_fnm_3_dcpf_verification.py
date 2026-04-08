"""
Test G-FNM-3: DCPF verification against reference solution on LARGE

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01, 28000-bus main island)
Pass condition: Pass if all aggregate thresholds are met and no hard-fail condition
  is triggered, per the dcpf section of data/fnm/reference/pass_conditions.json.
  Bus injection power balance check must pass.
  Deviation values in scientific notation.
Tool: PyPSA 1.1.2
Input: MATPOWER fallback (data/fnm/reference/cleaned/fnm_main_island.m)
Protocol: v11, skill v2, test_hash 64141acc
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

# Make shared matpower_loader importable
sys.path.insert(0, "/workspace/evaluations/shared")

CLEANED_M = Path("/workspace/data/fnm/reference/cleaned/fnm_main_island.m")
REF_BUSES = Path("/workspace/data/fnm/reference/dcpf/buses_dcpf.csv")
REF_BRANCHES = Path("/workspace/data/fnm/reference/dcpf/branches_dcpf.csv")
PASS_CONDITIONS = Path("/workspace/data/fnm/reference/pass_conditions.json")
EXCLUDED_BUSES = Path("/workspace/data/fnm/reference/excluded_buses.json")


def _sci(val: float) -> str:
    """Format a float in scientific notation with 6 decimal places."""
    return f"{val:.6e}"


def run() -> dict:
    """Execute G-FNM-3 DCPF verification and return structured results."""
    import tracemalloc

    import pandas as pd
    import pypsa
    from matpower_loader import load_pypsa
    from matpowercaseframes import CaseFrames

    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # ── 1. Load pass conditions and reference data ──────────────────
        with open(PASS_CONDITIONS) as f:
            pass_conds = json.load(f)

        dcpf_conds = pass_conds["dcpf"]
        VA_TOL_DEG = dcpf_conds["aggregate"]["bus_angle"]["va_tolerance_deg"]
        BUS_PASS_FRAC = dcpf_conds["aggregate"]["bus_angle"]["min_passing_fraction"]
        P_TOL_PCT = dcpf_conds["aggregate"]["branch_flow"]["p_tolerance_pct"]
        P_BASE_FLOOR = dcpf_conds["aggregate"]["branch_flow"]["p_base_floor_mw"]
        BRANCH_PASS_FRAC = dcpf_conds["aggregate"]["branch_flow"]["min_passing_fraction"]
        HARD_FAIL_BUS_FRAC = dcpf_conds["hard_fail"]["conditions"][0]["threshold"]
        HARD_FAIL_BRANCH_FRAC = dcpf_conds["hard_fail"]["conditions"][1]["threshold"]
        HARD_FAIL_MAX_DEV_PCT = dcpf_conds["hard_fail"]["conditions"][2]["threshold_pct"]

        results["details"]["pass_thresholds"] = {
            "bus_va_tol_deg": VA_TOL_DEG,
            "bus_min_pass_frac": BUS_PASS_FRAC,
            "branch_p_tol_pct": P_TOL_PCT,
            "branch_p_base_floor_mw": P_BASE_FLOOR,
            "branch_min_pass_frac": BRANCH_PASS_FRAC,
        }

        # Load excluded buses
        with open(EXCLUDED_BUSES) as f:
            excl_data = json.load(f)
        excluded_bus_set = {int(b["bus_number"]) for b in excl_data.get("excluded_buses", [])}
        results["details"]["excluded_buses_count"] = len(excluded_bus_set)

        # Load reference data
        ref_buses_df = pd.read_csv(REF_BUSES)
        ref_branches_df = pd.read_csv(REF_BRANCHES)

        results["details"]["reference_counts"] = {
            "ref_buses": len(ref_buses_df),
            "ref_branches": len(ref_branches_df),
        }
        results["details"]["tool_version"] = pypsa.__version__

        # ── 2. Load cleaned MATPOWER case via shared matpower_loader ──
        net = load_pypsa(str(CLEANED_M), overwrite_zero_s_nom=100000.0)
        net.set_snapshots([0])

        # Also load raw arrays for branch comparison analysis
        cf = CaseFrames(str(CLEANED_M))
        bus_array = cf.bus.values
        gen_array = cf.gen.values
        branch_array = cf.branch.values
        baseMVA = float(cf.baseMVA)

        results["details"]["baseMVA"] = baseMVA
        results["details"]["input_path"] = "matpower"

        branch_status = branch_array[:, 10].astype(int)
        n_active = int((branch_status == 1).sum())

        results["details"]["matpower_counts"] = {
            "buses": int(bus_array.shape[0]),
            "branches_total": int(branch_array.shape[0]),
            "branches_active": n_active,
            "generators": int(gen_array.shape[0]),
        }

        results["workarounds"].append(
            "MATPOWER fallback: G-FNM-1 failed (psse_parse_error). Loaded from "
            "pre-cleaned MATPOWER .m file via shared matpower_loader.load_pypsa() "
            "(applies branch status, transformer susceptance, and gencost patches)."
        )

        n_lines = len(net.lines)
        n_xfmrs = len(net.transformers)
        results["details"]["pypsa_counts"] = {
            "buses": len(net.buses),
            "lines": n_lines,
            "transformers": n_xfmrs,
            "total_branches": n_lines + n_xfmrs,
            "generators": len(net.generators),
            "loads": len(net.loads),
        }

        # ── 3. Run DCPF (lpf) ──────────────────────────────────────────
        tracemalloc.start()
        t_solve_start = time.perf_counter()
        net.lpf()
        t_solve = time.perf_counter() - t_solve_start
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mem_mb = peak_mem / (1024 * 1024)

        results["details"]["solve_wall_clock_seconds"] = round(t_solve, 4)
        results["details"]["peak_memory_mb"] = round(peak_mem_mb, 1)

        # ── 4. Extract PyPSA results ────────────────────────────────────
        if hasattr(net, "buses_t") and "v_ang" in net.buses_t and len(net.buses_t.v_ang) > 0:
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

        # ── 5. Compare bus voltage angles ───────────────────────────────
        ref_bus_va = {
            int(row["bus_number"]): float(row["va_deg"]) for _, row in ref_buses_df.iterrows()
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

        va_deviations = np.array(va_deviations)
        n_nonexcl_buses = len(va_deviations)
        buses_passing = int(np.sum(va_deviations <= VA_TOL_DEG))
        bus_pass_frac = float(buses_passing / n_nonexcl_buses) if n_nonexcl_buses > 0 else 0.0

        results["details"]["bus_angle_comparison"] = {
            "non_excluded_buses_matched": n_nonexcl_buses,
            "tolerance_deg": VA_TOL_DEG,
            "buses_passing": buses_passing,
            "fraction_passing": round(bus_pass_frac, 6),
            "max_deviation_deg": _sci(float(np.max(va_deviations)))
            if len(va_deviations) > 0
            else None,
            "mean_deviation_deg": _sci(float(np.mean(va_deviations)))
            if len(va_deviations) > 0
            else None,
            "median_deviation_deg": _sci(float(np.median(va_deviations)))
            if len(va_deviations) > 0
            else None,
            "p95_deviation_deg": _sci(float(np.percentile(va_deviations, 95)))
            if len(va_deviations) > 0
            else None,
            "p99_deviation_deg": _sci(float(np.percentile(va_deviations, 99)))
            if len(va_deviations) > 0
            else None,
        }

        # Voltage-level tier breakdown
        ref_bus_kv = {
            int(row["bus_number"]): float(row["base_kv"]) for _, row in ref_buses_df.iterrows()
        }
        tier_labels = {
            "transmission_230kv_plus": (230.0, float("inf")),
            "subtransmission_69_to_229kv": (69.0, 230.0),
            "distribution_below_69kv": (0.0, 69.0),
        }
        tier_stats = {}
        for label, (kv_min, kv_max) in tier_labels.items():
            tier_devs = []
            for i, bus_num in enumerate(va_bus_numbers):
                kv = ref_bus_kv.get(bus_num, 0)
                if kv_min <= kv < kv_max:
                    tier_devs.append(va_deviations[i])
            tier_devs_arr = np.array(tier_devs) if tier_devs else np.array([])
            if len(tier_devs_arr) > 0:
                tier_pass = int(np.sum(tier_devs_arr <= VA_TOL_DEG))
                tier_stats[label] = {
                    "count": len(tier_devs_arr),
                    "passing": tier_pass,
                    "fraction_passing": round(tier_pass / len(tier_devs_arr), 6),
                    "max_deviation_deg": _sci(float(np.max(tier_devs_arr))),
                    "mean_deviation_deg": _sci(float(np.mean(tier_devs_arr))),
                }
            else:
                tier_stats[label] = {"count": 0}
        results["details"]["bus_angle_by_voltage_tier"] = tier_stats

        # ── 6. Hard-fail checks on buses ─────────────────────────────────
        bus_failing_frac = 1.0 - bus_pass_frac
        hard_fail_bus = bus_failing_frac > HARD_FAIL_BUS_FRAC
        if hard_fail_bus:
            results["errors"].append(
                f"HARD FAIL: {bus_failing_frac:.1%} of buses fail VA tolerance "
                f"(threshold {HARD_FAIL_BUS_FRAC:.0%})"
            )

        # ── 7. Compare branch power flows ──────────────────────────────
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
        p_deviations_mw = []
        p_dev_lines = []
        p_dev_xfmrs = []
        max_dev_pct = 0.0
        max_dev_mw = 0.0
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
                abs_dev_mw = abs(float(pypsa_p) - ref_p)
                denom = max(abs(ref_p), P_BASE_FLOOR)
                dev_pct = (abs_dev_mw / denom) * 100.0
                p_deviations_pct.append(dev_pct)
                p_deviations_mw.append(abs_dev_mw)
                if dev_pct > max_dev_pct:
                    max_dev_pct = dev_pct
                if abs_dev_mw > max_dev_mw:
                    max_dev_mw = abs_dev_mw
                if comp_type == "line":
                    p_dev_lines.append(dev_pct)
                else:
                    p_dev_xfmrs.append(dev_pct)

            active_row += 1

        p_deviations_pct = np.array(p_deviations_pct)
        p_deviations_mw = np.array(p_deviations_mw)
        n_branches_matched = len(p_deviations_pct)
        branches_passing = int(np.sum(p_deviations_pct < P_TOL_PCT))
        branch_pass_frac = (
            float(branches_passing / n_branches_matched) if n_branches_matched > 0 else 0.0
        )

        results["details"]["branch_flow_comparison"] = {
            "matched_branches": n_branches_matched,
            "tolerance_pct": P_TOL_PCT,
            "p_base_floor_mw": P_BASE_FLOOR,
            "branches_passing": branches_passing,
            "fraction_passing": round(branch_pass_frac, 6),
            "max_deviation_pct": _sci(float(max_dev_pct)),
            "max_deviation_mw": _sci(float(max_dev_mw)),
            "mean_deviation_pct": _sci(float(np.mean(p_deviations_pct)))
            if len(p_deviations_pct) > 0
            else None,
            "median_deviation_pct": _sci(float(np.median(p_deviations_pct)))
            if len(p_deviations_pct) > 0
            else None,
            "p95_deviation_pct": _sci(float(np.percentile(p_deviations_pct, 95)))
            if len(p_deviations_pct) > 0
            else None,
            "p99_deviation_pct": _sci(float(np.percentile(p_deviations_pct, 99)))
            if len(p_deviations_pct) > 0
            else None,
        }

        results["details"]["branch_flow_by_type"] = {
            "lines": {
                "count": len(p_dev_lines),
                "mean_deviation_pct": _sci(float(np.mean(p_dev_lines))) if p_dev_lines else None,
                "max_deviation_pct": _sci(float(np.max(p_dev_lines))) if p_dev_lines else None,
            },
            "transformers": {
                "count": len(p_dev_xfmrs),
                "mean_deviation_pct": _sci(float(np.mean(p_dev_xfmrs))) if p_dev_xfmrs else None,
                "max_deviation_pct": _sci(float(np.max(p_dev_xfmrs))) if p_dev_xfmrs else None,
            },
        }

        # ── 8. Hard-fail checks on branches ──────────────────────────────
        branch_failing_frac = 1.0 - branch_pass_frac
        hard_fail_branch = branch_failing_frac > HARD_FAIL_BRANCH_FRAC
        hard_fail_max = max_dev_pct > HARD_FAIL_MAX_DEV_PCT
        if hard_fail_branch:
            results["errors"].append(
                f"HARD FAIL: {branch_failing_frac:.1%} of branches fail P tolerance "
                f"(threshold {HARD_FAIL_BRANCH_FRAC:.0%})"
            )
        if hard_fail_max:
            results["errors"].append(
                f"HARD FAIL: max branch deviation {max_dev_pct:.1f}% exceeds "
                f"{HARD_FAIL_MAX_DEV_PCT:.0f}% hard-fail threshold"
            )

        # ── 9. Transformer tap analysis ─────────────────────────────────
        taps = branch_array[:, 8]
        taps_xfmr = taps[is_xfmr]
        taps_xfmr = np.where(taps_xfmr == 0, 1.0, taps_xfmr)
        n_nonunity = int((taps_xfmr != 1.0).sum())
        results["details"]["transformer_tap_analysis"] = {
            "total_transformers": int(is_xfmr.sum()),
            "tap_eq_1": int(is_xfmr.sum()) - n_nonunity,
            "tap_ne_1": n_nonunity,
            "tap_range": [round(float(taps_xfmr.min()), 4), round(float(taps_xfmr.max()), 4)],
            "formulation_note": (
                "Transformer susceptance patched by matpower_loader.load_pypsa() "
                "to b=1/x (MATPOWER convention), overriding PyPSA's default "
                "b=1/(x*tap). This aligns the DC B-matrix formulation with the "
                "reference DCPF solution."
            ),
        }

        # ── 10. Bus injection power balance check ─────────────────────────
        # For DCPF, verify that net injection (generation - load) at each bus
        # equals the sum of branch flows out of that bus, within numerical tolerance.
        # Use post-solve generator output (p) which includes slack bus adjustment.
        if hasattr(net, "generators_t") and "p" in net.generators_t and len(net.generators_t.p) > 0:
            gen_p_series = net.generators_t.p.iloc[0]
        else:
            gen_p_series = net.generators.get("p", net.generators["p_set"])

        bus_gen_inject = {}
        for gen_name in net.generators.index:
            bus = str(net.generators.at[gen_name, "bus"])
            gen_p = (
                float(gen_p_series.get(gen_name, 0.0)) if gen_name in gen_p_series.index else 0.0
            )
            bus_gen_inject[bus] = bus_gen_inject.get(bus, 0.0) + gen_p

        bus_load_inject = {}
        for load_name, load_row in net.loads.iterrows():
            bus = str(load_row["bus"])
            bus_load_inject[bus] = bus_load_inject.get(bus, 0.0) + float(load_row["p_set"])

        # Bus net injection = generation - load
        bus_net_injection = {}
        all_buses = set(net.buses.index)
        for bus in all_buses:
            bus_net_injection[bus] = bus_gen_inject.get(bus, 0.0) - bus_load_inject.get(bus, 0.0)

        # Sum of branch flows leaving each bus (p0 = flow from bus0, p1 = flow from bus1)
        bus_flow_out = {bus: 0.0 for bus in all_buses}

        # Lines: p0 at bus0, p1 at bus1
        if hasattr(net, "lines_t") and "p0" in net.lines_t and len(net.lines_t.p0) > 0:
            line_p0_vals = net.lines_t.p0.iloc[0]
            line_p1_vals = net.lines_t.p1.iloc[0]
        else:
            line_p0_vals = net.lines.get("p0", pd.Series(dtype=float))
            line_p1_vals = net.lines.get("p1", pd.Series(dtype=float))

        for line_name in net.lines.index:
            if not net.lines.at[line_name, "active"]:
                continue
            bus0 = str(net.lines.at[line_name, "bus0"])
            bus1 = str(net.lines.at[line_name, "bus1"])
            p0 = float(line_p0_vals.get(line_name, 0.0)) if line_name in line_p0_vals.index else 0.0
            p1 = float(line_p1_vals.get(line_name, 0.0)) if line_name in line_p1_vals.index else 0.0
            bus_flow_out[bus0] = bus_flow_out.get(bus0, 0.0) + p0
            bus_flow_out[bus1] = bus_flow_out.get(bus1, 0.0) + p1

        # Transformers
        if (
            hasattr(net, "transformers_t")
            and "p0" in net.transformers_t
            and len(net.transformers_t.p0) > 0
        ):
            xfmr_p0_vals = net.transformers_t.p0.iloc[0]
            xfmr_p1_vals = net.transformers_t.p1.iloc[0]
        else:
            xfmr_p0_vals = net.transformers.get("p0", pd.Series(dtype=float))
            xfmr_p1_vals = net.transformers.get("p1", pd.Series(dtype=float))

        for xfmr_name in net.transformers.index:
            if not net.transformers.at[xfmr_name, "active"]:
                continue
            bus0 = str(net.transformers.at[xfmr_name, "bus0"])
            bus1 = str(net.transformers.at[xfmr_name, "bus1"])
            p0 = float(xfmr_p0_vals.get(xfmr_name, 0.0)) if xfmr_name in xfmr_p0_vals.index else 0.0
            p1 = float(xfmr_p1_vals.get(xfmr_name, 0.0)) if xfmr_name in xfmr_p1_vals.index else 0.0
            bus_flow_out[bus0] = bus_flow_out.get(bus0, 0.0) + p0
            bus_flow_out[bus1] = bus_flow_out.get(bus1, 0.0) + p1

        # Check: net_injection = sum_of_flows_out for each bus (DCPF is lossless)
        # In DCPF, p0 + p1 = 0 for each branch (lossless), so
        # net_injection_bus = sum_of_p0_leaving_bus (positive = outflow)
        balance_mismatches = []
        for bus in all_buses:
            try:
                bus_num = int(bus)
            except (ValueError, TypeError):
                continue
            if bus_num in excluded_bus_set:
                continue
            net_inj = bus_net_injection.get(bus, 0.0)
            flow_out = bus_flow_out.get(bus, 0.0)
            mismatch = abs(net_inj - flow_out)
            balance_mismatches.append(mismatch)

        balance_mismatches = np.array(balance_mismatches)
        # Tolerance: 1e-3 MW (0.001 MW) for numerical noise
        BALANCE_TOL_MW = 1e-3
        buses_balanced = int(np.sum(balance_mismatches <= BALANCE_TOL_MW))
        balance_pass = buses_balanced == len(balance_mismatches)

        results["details"]["power_balance_check"] = {
            "buses_checked": len(balance_mismatches),
            "tolerance_mw": BALANCE_TOL_MW,
            "buses_balanced": buses_balanced,
            "buses_imbalanced": len(balance_mismatches) - buses_balanced,
            "max_mismatch_mw": _sci(float(np.max(balance_mismatches)))
            if len(balance_mismatches) > 0
            else None,
            "mean_mismatch_mw": _sci(float(np.mean(balance_mismatches)))
            if len(balance_mismatches) > 0
            else None,
            "balance_pass": balance_pass,
        }

        if not balance_pass:
            n_imbal = len(balance_mismatches) - buses_balanced
            results["errors"].append(
                f"Bus injection power balance failed: {n_imbal} buses exceed "
                f"{BALANCE_TOL_MW} MW tolerance "
                f"(max mismatch: {_sci(float(np.max(balance_mismatches)))} MW)"
            )

        # ── 11. Power balance (system-level) ──────────────────────────────
        total_gen_mw = float(net.generators.p_set.sum())
        total_load_mw = float(net.loads.p_set.sum())
        results["details"]["power_balance"] = {
            "total_gen_mw_presolve": round(total_gen_mw, 3),
            "total_load_mw": round(total_load_mw, 3),
        }

        # ── 12. Pass/fail determination ──────────────────────────────────
        hard_fail = hard_fail_bus or hard_fail_branch or hard_fail_max
        bus_pass = bus_pass_frac >= BUS_PASS_FRAC
        branch_pass = branch_pass_frac >= BRANCH_PASS_FRAC

        results["details"]["pass_evaluation"] = {
            "bus_angle_pass": bus_pass,
            "bus_angle_fraction": round(bus_pass_frac, 6),
            "bus_angle_required": BUS_PASS_FRAC,
            "branch_flow_pass": branch_pass,
            "branch_flow_fraction": round(branch_pass_frac, 6),
            "branch_flow_required": BRANCH_PASS_FRAC,
            "hard_fail_triggered": hard_fail,
            "balance_pass": balance_pass,
        }

        if hard_fail:
            results["status"] = "fail"
        elif bus_pass and branch_pass and balance_pass:
            results["status"] = "pass"
        else:
            results["status"] = "fail"
            if not bus_pass:
                results["errors"].append(
                    f"Bus angle tolerance not met: {bus_pass_frac:.4%} within "
                    f"{VA_TOL_DEG} deg (need {BUS_PASS_FRAC:.0%})."
                )
            if not branch_pass:
                results["errors"].append(
                    f"Branch flow tolerance not met: {branch_pass_frac:.4%} within "
                    f"tolerance (need {BRANCH_PASS_FRAC:.0%})."
                )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 3)

    return results


if __name__ == "__main__":
    import json as _json

    result = run()
    print(_json.dumps(result, indent=2, default=str))
