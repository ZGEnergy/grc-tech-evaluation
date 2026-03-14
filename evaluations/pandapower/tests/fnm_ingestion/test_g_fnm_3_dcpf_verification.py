"""
Test G-FNM-3: DCPF verification against reference solution on FNM

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: Pass if all aggregate thresholds are met and no hard-fail
    condition is triggered, per the dcpf section of pass_conditions.json.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import time
import traceback

import numpy as np
import pandas as pd


def run(
    case_file: str = "/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
    ref_buses_file: str = "/workspace/data/fnm/reference/dcpf/buses_dcpf.csv",
    ref_branches_file: str = "/workspace/data/fnm/reference/dcpf/branches_dcpf.csv",
    excluded_buses_file: str = "/workspace/data/fnm/reference/excluded_buses.json",
) -> dict:
    """Execute the G-FNM-3 DCPF verification test.

    Uses pre-cleaned MATPOWER case (main island only) as input.
    Compares DCPF results against reference solution.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandapower as pp
        from matpowercaseframes import CaseFrames
        from pandapower.converter.pypower.from_ppc import from_ppc

        # --- Load excluded buses ---
        with open(excluded_buses_file) as f:
            excl_data = json.load(f)
        excluded_bus_set = {b["bus_number"] for b in excl_data["excluded_buses"]}

        # --- Load reference DCPF solution ---
        ref_buses = pd.read_csv(ref_buses_file)
        ref_branches = pd.read_csv(ref_branches_file)

        # --- Load FNM main island into pandapower ---
        cf = CaseFrames(case_file)
        branch = cf.branch.values.copy()

        # Workaround: set zero RATE_A to 9999 (same as G-FNM-1)
        rate_a_col = 5
        zero_rate_mask = np.isclose(branch[:, rate_a_col], 0)
        branch[zero_rate_mask, rate_a_col] = 9999.0

        ppc = {
            "version": "2",
            "baseMVA": cf.baseMVA,
            "bus": cf.bus.values,
            "gen": cf.gen.values,
            "branch": branch,
        }

        t_load_start = time.perf_counter()
        net = from_ppc(ppc, f_hz=60)
        t_load = time.perf_counter() - t_load_start

        results["details"]["load_time_seconds"] = t_load
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["input_path"] = "matpower"
        results["details"]["baseMVA"] = net.sn_mva

        # --- Solve DCPF ---
        t_solve_start = time.perf_counter()
        pp.rundcpp(net)
        t_solve = time.perf_counter() - t_solve_start

        results["details"]["solve_time_seconds"] = t_solve

        if not net["converged"]:
            results["errors"].append("DCPF did not converge")
            return results

        # --- Extract tool results ---
        tool_va = net.res_bus["va_degree"]
        tool_bus_numbers = net.bus.index.tolist()

        # Build a lookup from bus number -> tool VA
        tool_va_dict = dict(zip(tool_bus_numbers, tool_va))

        # --- Bus angle comparison ---
        # Filter reference buses: exclude excluded buses, keep only buses in tool
        ref_buses_filtered = ref_buses[
            (~ref_buses["bus_number"].isin(excluded_bus_set))
            & (ref_buses["bus_number"].isin(tool_va_dict.keys()))
        ].copy()

        ref_buses_filtered["va_tool"] = ref_buses_filtered["bus_number"].map(tool_va_dict)
        ref_buses_filtered["va_dev_deg"] = (
            ref_buses_filtered["va_tool"] - ref_buses_filtered["va_deg"]
        ).abs()

        va_tolerance_deg = 1.0
        min_passing_fraction = 0.95

        total_non_excluded = len(ref_buses_filtered)
        passing_buses = ref_buses_filtered[ref_buses_filtered["va_dev_deg"] < va_tolerance_deg]
        failing_buses = ref_buses_filtered[ref_buses_filtered["va_dev_deg"] >= va_tolerance_deg]

        bus_passing_count = len(passing_buses)
        bus_failing_count = len(failing_buses)
        bus_passing_frac = bus_passing_count / total_non_excluded if total_non_excluded > 0 else 0

        bus_angle_pass = bus_passing_frac >= min_passing_fraction

        # --- Branch flow comparison ---
        # Build list of tool branch flows in PPC branch order.
        # pandapower's from_ppc creates elements in the same order as the PPC
        # branch matrix rows. Lines come first, then trafos, then impedances.
        # The reference DCPF CSV is also in PPC branch order.
        #
        # To handle parallel branches correctly, we match by row order rather
        # than by (from_bus, to_bus) key.

        # Collect all tool branch flows in PPC branch order
        tool_branch_list = []

        # Lines (created first in from_ppc)
        for idx in net.line.index:
            fb = int(net.line.at[idx, "from_bus"])
            tb = int(net.line.at[idx, "to_bus"])
            p_mw = net.res_line.at[idx, "p_from_mw"]
            in_service = net.line.at[idx, "in_service"]
            tool_branch_list.append(
                {
                    "from_bus": fb,
                    "to_bus": tb,
                    "p_mw": p_mw,
                    "in_service": in_service,
                    "element": "line",
                }
            )

        # Trafos (created next)
        for idx in net.trafo.index:
            fb = int(net.trafo.at[idx, "hv_bus"])
            tb = int(net.trafo.at[idx, "lv_bus"])
            p_mw = net.res_trafo.at[idx, "p_hv_mw"]
            in_service = net.trafo.at[idx, "in_service"]
            tool_branch_list.append(
                {
                    "from_bus": fb,
                    "to_bus": tb,
                    "p_mw": p_mw,
                    "in_service": in_service,
                    "element": "trafo",
                }
            )

        # Impedances (created last)
        for idx in net.impedance.index:
            fb = int(net.impedance.at[idx, "from_bus"])
            tb = int(net.impedance.at[idx, "to_bus"])
            p_mw = net.res_impedance.at[idx, "p_from_mw"]
            in_service = net.impedance.at[idx, "in_service"]
            tool_branch_list.append(
                {
                    "from_bus": fb,
                    "to_bus": tb,
                    "p_mw": p_mw,
                    "in_service": in_service,
                    "element": "impedance",
                }
            )

        # Match reference branches to tool by row order
        # Both should be in PPC branch matrix order
        ref_branches_in_service = ref_branches[ref_branches["status"] == 1].copy()
        matched = []
        unmatched = 0

        # Build a multi-map from (from_bus, to_bus) -> list of tool flows
        from collections import defaultdict

        tool_flow_map = defaultdict(list)
        for tb_entry in tool_branch_list:
            if tb_entry["in_service"]:
                key = (tb_entry["from_bus"], tb_entry["to_bus"])
                tool_flow_map[key].append(tb_entry["p_mw"])

        # Track consumption of parallel branches
        tool_flow_consumed = defaultdict(int)

        for _, row in ref_branches_in_service.iterrows():
            fb = int(row["from_bus"])
            tb = int(row["to_bus"])
            ref_flow = row["pf_mw"]

            # Try forward direction
            key_fwd = (fb, tb)
            key_rev = (tb, fb)

            if key_fwd in tool_flow_map and tool_flow_consumed[key_fwd] < len(
                tool_flow_map[key_fwd]
            ):
                idx = tool_flow_consumed[key_fwd]
                tool_flow = tool_flow_map[key_fwd][idx]
                tool_flow_consumed[key_fwd] += 1
                matched.append({"from_bus": fb, "to_bus": tb, "ref": ref_flow, "tool": tool_flow})
            elif key_rev in tool_flow_map and tool_flow_consumed[key_rev] < len(
                tool_flow_map[key_rev]
            ):
                idx = tool_flow_consumed[key_rev]
                tool_flow = -tool_flow_map[key_rev][idx]
                tool_flow_consumed[key_rev] += 1
                matched.append({"from_bus": fb, "to_bus": tb, "ref": ref_flow, "tool": tool_flow})
            else:
                unmatched += 1

        matched_df = pd.DataFrame(matched)

        if len(matched_df) == 0:
            results["errors"].append("No reference branches matched to tool branches")
            return results

        # Compute deviation per pass_conditions.json
        p_base_floor_mw = 1.0
        p_tolerance_pct = 10.0
        min_branch_passing_frac = 0.9

        matched_df["abs_ref"] = matched_df["ref"].abs()
        matched_df["deviation_mw"] = (matched_df["tool"] - matched_df["ref"]).abs()
        matched_df["deviation_pct"] = (
            matched_df["deviation_mw"]
            / matched_df[["abs_ref"]].clip(lower=p_base_floor_mw).values.flatten()
            * 100
        )

        branch_passing = matched_df[matched_df["deviation_pct"] < p_tolerance_pct]
        branch_failing = matched_df[matched_df["deviation_pct"] >= p_tolerance_pct]

        total_in_service = len(matched_df)
        branch_passing_count = len(branch_passing)
        branch_failing_count = len(branch_failing)
        branch_passing_frac = branch_passing_count / total_in_service if total_in_service > 0 else 0

        branch_flow_pass = branch_passing_frac >= min_branch_passing_frac

        # --- Hard-fail checks ---
        hard_fail = False
        hard_fail_reasons = []

        # Check 1: excessive bus failing fraction > 0.2
        bus_failing_frac = bus_failing_count / total_non_excluded if total_non_excluded > 0 else 0
        if bus_failing_frac > 0.2:
            hard_fail = True
            hard_fail_reasons.append(
                f"Excessive bus failing fraction: {bus_failing_frac:.3f} > 0.2"
            )

        # Check 2: excessive branch failing fraction > 0.2
        branch_failing_frac = branch_failing_count / total_in_service if total_in_service > 0 else 0
        if branch_failing_frac > 0.2:
            hard_fail = True
            hard_fail_reasons.append(
                f"Excessive branch failing fraction: {branch_failing_frac:.3f} > 0.2"
            )

        # Check 3: extreme branch flow deviation > 50%
        max_deviation_pct = matched_df["deviation_pct"].max() if len(matched_df) > 0 else 0
        if max_deviation_pct > 50.0:
            hard_fail = True
            hard_fail_reasons.append(
                f"Extreme branch flow deviation: {max_deviation_pct:.1f}% > 50%"
            )

        # --- Voltage level breakdown (informational) ---
        ref_buses_filtered_with_kv = ref_buses_filtered.copy()
        voltage_tiers = [
            ("transmission_230kv_plus", 230.0, None),
            ("subtransmission_69_to_229kv", 69.0, 230.0),
            ("distribution_below_69kv", 0.0, 69.0),
        ]
        tier_results = {}
        for label, min_kv, max_kv in voltage_tiers:
            mask = ref_buses_filtered_with_kv["base_kv"] >= min_kv
            if max_kv is not None:
                mask = mask & (ref_buses_filtered_with_kv["base_kv"] < max_kv)
            tier_buses = ref_buses_filtered_with_kv[mask]
            if len(tier_buses) > 0:
                tier_passing = tier_buses[tier_buses["va_dev_deg"] < va_tolerance_deg]
                tier_results[label] = {
                    "total": len(tier_buses),
                    "passing": len(tier_passing),
                    "fraction": len(tier_passing) / len(tier_buses),
                    "max_dev_deg": float(tier_buses["va_dev_deg"].max()),
                    "mean_dev_deg": float(tier_buses["va_dev_deg"].mean()),
                }

        # --- Outlier analysis (top 20 failing buses by deviation) ---
        top_outliers = []
        if len(failing_buses) > 0:
            top_20 = failing_buses.nlargest(20, "va_dev_deg")
            for _, row in top_20.iterrows():
                top_outliers.append(
                    {
                        "bus_number": int(row["bus_number"]),
                        "va_ref_deg": float(row["va_deg"]),
                        "va_tool_deg": float(row["va_tool"]),
                        "deviation_deg": float(row["va_dev_deg"]),
                        "base_kv": float(row["base_kv"]),
                        "bus_type": int(row["bus_type"]),
                    }
                )

        # --- Branch outlier analysis (top 20 failing branches) ---
        top_branch_outliers = []
        if len(branch_failing) > 0:
            top_20_br = branch_failing.nlargest(20, "deviation_pct")
            for _, row in top_20_br.iterrows():
                top_branch_outliers.append(
                    {
                        "from_bus": int(row["from_bus"]),
                        "to_bus": int(row["to_bus"]),
                        "ref_mw": float(row["ref"]),
                        "tool_mw": float(row["tool"]),
                        "deviation_pct": float(row["deviation_pct"]),
                    }
                )

        # --- Formulation difference classification ---
        formulation_diff_note = ""
        if not bus_angle_pass or not branch_flow_pass:
            # Check if deviations correlate with transformer-connected buses
            # pandapower uses full B-matrix (like MATPOWER), so formulation
            # differences should be minimal.
            formulation_diff_note = (
                "pandapower uses MATPOWER-equivalent full B-matrix construction "
                "that incorporates tap ratios and phase shift angles. "
                "Deviations, if any, are expected to be data ingestion related "
                "rather than formulation differences."
            )

        # --- Aggregate metrics ---
        bus_va_stats = {
            "max_deg": float(ref_buses_filtered["va_dev_deg"].max()),
            "mean_deg": float(ref_buses_filtered["va_dev_deg"].mean()),
            "median_deg": float(ref_buses_filtered["va_dev_deg"].median()),
            "p95_deg": float(ref_buses_filtered["va_dev_deg"].quantile(0.95)),
            "p99_deg": float(ref_buses_filtered["va_dev_deg"].quantile(0.99)),
        }

        branch_flow_stats = {}
        if len(matched_df) > 0:
            branch_flow_stats = {
                "max_pct": float(matched_df["deviation_pct"].max()),
                "mean_pct": float(matched_df["deviation_pct"].mean()),
                "median_pct": float(matched_df["deviation_pct"].median()),
                "p95_pct": float(matched_df["deviation_pct"].quantile(0.95)),
                "p99_pct": float(matched_df["deviation_pct"].quantile(0.99)),
                "max_abs_mw": float(matched_df["deviation_mw"].max()),
            }

        results["details"] = {
            **results["details"],
            "bus_angle": {
                "total_non_excluded": total_non_excluded,
                "passing": bus_passing_count,
                "failing": bus_failing_count,
                "passing_fraction": bus_passing_frac,
                "threshold": min_passing_fraction,
                "tolerance_deg": va_tolerance_deg,
                "pass": bus_angle_pass,
                "stats": bus_va_stats,
            },
            "branch_flow": {
                "total_in_service": total_in_service,
                "matched": len(matched_df),
                "unmatched": unmatched,
                "passing": branch_passing_count,
                "failing": branch_failing_count,
                "passing_fraction": branch_passing_frac,
                "threshold": min_branch_passing_frac,
                "tolerance_pct": p_tolerance_pct,
                "pass": branch_flow_pass,
                "stats": branch_flow_stats,
            },
            "hard_fail": {
                "triggered": hard_fail,
                "reasons": hard_fail_reasons,
            },
            "voltage_tiers": tier_results,
            "top_bus_outliers": top_outliers,
            "top_branch_outliers": top_branch_outliers,
            "formulation_note": formulation_diff_note,
        }

        # --- Determine overall status ---
        if hard_fail:
            results["status"] = "fail"
            results["errors"].extend(hard_fail_reasons)
        elif bus_angle_pass and branch_flow_pass:
            results["status"] = "pass"
        else:
            # Check for formulation_difference classification
            if not bus_angle_pass:
                results["errors"].append(
                    f"Bus angle passing fraction {bus_passing_frac:.3f} < {min_passing_fraction}"
                )
            if not branch_flow_pass:
                results["errors"].append(
                    f"Branch flow passing fraction {branch_passing_frac:.3f} < {min_branch_passing_frac}"
                )
            results["status"] = "fail"

        results["workarounds"] = [
            "MATPOWER fallback: used pre-cleaned fnm_main_island.mat instead of "
            "intermediate CSVs (pandapower has no native CSV import).",
            "Zero RATE_A branches set to 9999 before from_ppc (same as G-FNM-1).",
        ]

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
