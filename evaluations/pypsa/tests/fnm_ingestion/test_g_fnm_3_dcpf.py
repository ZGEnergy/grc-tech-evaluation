"""G-FNM-3: DCPF verification against MATPOWER reference solution.

Dimension: fnm_ingestion (Suite G)
Network: LARGE — FNM main island (28000 buses, 33000 active branches)
Pass condition:
  - >=99% of buses within 0.1 degree voltage angle tolerance
  - >=99% of in-service branches within 1 MW absolute (or 1% relative) tolerance
Tool: PyPSA 1.1.2

Note: PyPSA's DCPF (lpf) includes the tap ratio in the transformer susceptance
calculation (b = 1/(x * tap)), whereas MATPOWER's DCPF ignores the tap ratio
(b = 1/x). This is a known modeling difference that causes systematic deviations
on networks with many non-unity-tap transformers like the FNM.
"""

from __future__ import annotations

import json
import re
import time
import traceback
from pathlib import Path

import numpy as np

CLEANED_M = Path("/workspace/data/fnm/reference/cleaned/fnm_main_island.m")
REF_BUSES = Path("/workspace/data/fnm/reference/dcpf/buses_dcpf.csv")
REF_BRANCHES = Path("/workspace/data/fnm/reference/dcpf/branches_dcpf.csv")
REF_SUMMARY = Path("/workspace/data/fnm/reference/dcpf/summary_dcpf.json")

# Tolerances
VA_TOL_DEG = 0.1  # degrees
P_TOL_MW = 1.0  # MW absolute
P_TOL_REL = 0.01  # 1% relative
PASS_FRACTION = 0.99  # 99% of elements must be within tolerance


def parse_matpower_m(filepath: str | Path) -> dict:
    """Parse a MATPOWER .m case file into a PPC dict."""
    with open(filepath) as f:
        content = f.read()

    ppc: dict = {"version": "2"}

    m = re.search(r"mpc\.baseMVA\s*=\s*(\d+\.?\d*)", content)
    if m:
        ppc["baseMVA"] = float(m.group(1))

    for name in ["bus", "gen", "branch"]:
        pattern = rf"mpc\.{name}\s*=\s*\[(.*?)\];"
        m = re.search(pattern, content, re.DOTALL)
        if m:
            data = m.group(1).strip()
            rows = []
            for line in data.split("\n"):
                line = line.strip().rstrip(";")
                if "%" in line:
                    line = line[: line.index("%")]
                line = line.strip()
                if line:
                    vals = [float(x) for x in line.split()]
                    rows.append(vals)
            ppc[name] = np.array(rows)

    return ppc


def classify_branches(bus_array: np.ndarray, branch_array: np.ndarray) -> np.ndarray:
    """Replicate PyPSA's transformer vs line classification.

    A branch is a transformer if:
    - v_nom differs between from-bus and to-bus, OR
    - tap_ratio is not in {0, 1}, OR
    - phase_shift is nonzero.

    Returns boolean array (True = transformer).
    """
    bus_v_nom = dict(zip(bus_array[:, 0].astype(int), bus_array[:, 9]))
    n = branch_array.shape[0]
    is_xfmr = np.zeros(n, dtype=bool)
    for i in range(n):
        fbus = int(branch_array[i, 0])
        tbus = int(branch_array[i, 1])
        tap = branch_array[i, 8]
        shift = branch_array[i, 9]
        v0 = bus_v_nom.get(fbus, 0)
        v1 = bus_v_nom.get(tbus, 0)
        is_xfmr[i] = (v0 != v1) or (tap != 0.0 and tap != 1.0) or (shift != 0.0)
    return is_xfmr


def run() -> dict:
    """Execute G-FNM-3 DCPF verification and return structured results."""
    import tracemalloc

    import pandas as pd
    import pypsa

    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # ── 1. Load reference data ──────────────────────────────────────
        with open(REF_SUMMARY) as f:
            ref_summary = json.load(f)

        ref_buses_df = pd.read_csv(REF_BUSES)
        ref_branches_df = pd.read_csv(REF_BRANCHES)

        # ── 2. Parse cleaned MATPOWER .m case ────────────────────────────
        ppc = parse_matpower_m(CLEANED_M)
        baseMVA = ppc["baseMVA"]
        bus_array = ppc["bus"]
        gen_array = ppc["gen"]
        branch_array = ppc["branch"]

        results["details"]["baseMVA"] = baseMVA
        results["details"]["tool_version"] = pypsa.__version__

        n_buses_mat = bus_array.shape[0]
        n_branches_mat = branch_array.shape[0]
        n_gens_mat = gen_array.shape[0]

        branch_status = branch_array[:, 10].astype(int)
        n_active = int((branch_status == 1).sum())

        results["details"]["matpower_counts"] = {
            "buses": n_buses_mat,
            "branches_total": n_branches_mat,
            "branches_active": n_active,
            "generators": n_gens_mat,
        }

        results["workarounds"].append(
            "Parsed MATPOWER .m file with regex-based parser since the .mat file "
            "is Octave text format (not scipy-compatible) and PyPSA has no native "
            "MATPOWER reader."
        )

        # ── 3. Import into PyPSA ────────────────────────────────────────
        net = pypsa.Network()
        net.import_from_pypower_ppc(ppc)
        net.set_snapshots([0])

        n_lines = len(net.lines)
        n_xfmrs = len(net.transformers)
        results["details"]["pypsa_counts"] = {
            "buses": len(net.buses),
            "lines": n_lines,
            "transformers": n_xfmrs,
            "generators": len(net.generators),
            "loads": len(net.loads),
        }

        # ── 4. Run DCPF (lpf) ──────────────────────────────────────────
        tracemalloc.start()
        t_solve_start = time.perf_counter()
        net.lpf()
        t_solve = time.perf_counter() - t_solve_start
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mem_mb = peak_mem / (1024 * 1024)

        results["details"]["solve_wall_clock_seconds"] = round(t_solve, 4)
        results["details"]["peak_memory_mb"] = round(peak_mem_mb, 1)

        # ── 5. Extract PyPSA results ────────────────────────────────────
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

        # ── 6. Compare bus voltage angles ───────────────────────────────
        ref_bus_va = dict(zip(ref_buses_df["bus_number"].astype(str), ref_buses_df["va_deg"]))

        va_deviations = []
        for bus_name in pypsa_va_deg_series.index:
            bus_key = str(bus_name)
            if bus_key in ref_bus_va:
                dev = abs(float(pypsa_va_deg_series[bus_name]) - ref_bus_va[bus_key])
                va_deviations.append(dev)

        va_deviations = np.array(va_deviations)
        buses_within_tol = float(np.mean(va_deviations <= VA_TOL_DEG))

        results["details"]["bus_angle_comparison"] = {
            "matched_buses": len(va_deviations),
            "tolerance_deg": VA_TOL_DEG,
            "fraction_within_tolerance": round(buses_within_tol, 6),
            "max_deviation_deg": round(float(np.max(va_deviations)), 6),
            "mean_deviation_deg": round(float(np.mean(va_deviations)), 6),
            "median_deviation_deg": round(float(np.median(va_deviations)), 6),
            "p95_deviation_deg": round(float(np.percentile(va_deviations, 95)), 6),
            "p99_deviation_deg": round(float(np.percentile(va_deviations, 99)), 6),
        }

        # ── 7. Compare branch power flows ──────────────────────────────
        is_xfmr = classify_branches(bus_array, branch_array)
        n_xfmr_class = int(is_xfmr.sum())
        n_line_class = n_branches_mat - n_xfmr_class

        results["details"]["branch_classification"] = {
            "lines_classified": n_line_class,
            "transformers_classified": n_xfmr_class,
            "pypsa_lines": n_lines,
            "pypsa_transformers": n_xfmrs,
            "matches_pypsa": n_line_class == n_lines and n_xfmr_class == n_xfmrs,
        }

        # Build ordered mapping
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

        # Compare flows for active branches
        p_deviations = []
        p_ref_abs = []
        p_dev_lines = []
        p_dev_xfmrs = []
        active_row = 0

        for mat_row in range(n_branches_mat):
            if branch_status[mat_row] == 0:
                continue

            comp_type, comp_name = branch_pypsa_name[mat_row]
            if active_row >= len(ref_branches_df):
                break

            ref_p = float(ref_branches_df.iloc[active_row]["pf_mw"])

            if comp_type == "line":
                pypsa_p = line_p0_dict.get(comp_name, float("nan"))
            else:
                pypsa_p = xfmr_p0_dict.get(comp_name, float("nan"))

            if not np.isnan(pypsa_p):
                dev = abs(float(pypsa_p) - ref_p)
                p_deviations.append(dev)
                p_ref_abs.append(abs(ref_p))
                if comp_type == "line":
                    p_dev_lines.append(dev)
                else:
                    p_dev_xfmrs.append(dev)

            active_row += 1

        p_deviations = np.array(p_deviations)
        p_ref_abs = np.array(p_ref_abs)
        p_dev_lines = np.array(p_dev_lines)
        p_dev_xfmrs = np.array(p_dev_xfmrs)

        # Within tolerance: absolute OR relative
        within_abs = p_deviations <= P_TOL_MW
        safe_ref = np.where(p_ref_abs > 1e-6, p_ref_abs, 1.0)
        within_rel = p_deviations / safe_ref <= P_TOL_REL
        within_tol = within_abs | within_rel
        branches_within_tol = float(np.mean(within_tol))

        results["details"]["branch_flow_comparison"] = {
            "matched_branches": len(p_deviations),
            "tolerance_mw": P_TOL_MW,
            "tolerance_rel": P_TOL_REL,
            "fraction_within_tolerance": round(branches_within_tol, 6),
            "max_deviation_mw": round(float(np.max(p_deviations)), 4),
            "mean_deviation_mw": round(float(np.mean(p_deviations)), 4),
            "median_deviation_mw": round(float(np.median(p_deviations)), 4),
            "p95_deviation_mw": round(float(np.percentile(p_deviations, 95)), 4),
            "p99_deviation_mw": round(float(np.percentile(p_deviations, 99)), 4),
        }

        # Breakdown by component type
        results["details"]["branch_flow_by_type"] = {
            "lines": {
                "count": len(p_dev_lines),
                "mean_deviation_mw": round(float(np.mean(p_dev_lines)), 4)
                if len(p_dev_lines) > 0
                else None,
                "max_deviation_mw": round(float(np.max(p_dev_lines)), 4)
                if len(p_dev_lines) > 0
                else None,
                "p99_deviation_mw": round(float(np.percentile(p_dev_lines, 99)), 4)
                if len(p_dev_lines) > 0
                else None,
            },
            "transformers": {
                "count": len(p_dev_xfmrs),
                "mean_deviation_mw": round(float(np.mean(p_dev_xfmrs)), 4)
                if len(p_dev_xfmrs) > 0
                else None,
                "max_deviation_mw": round(float(np.max(p_dev_xfmrs)), 4)
                if len(p_dev_xfmrs) > 0
                else None,
                "p99_deviation_mw": round(float(np.percentile(p_dev_xfmrs, 99)), 4)
                if len(p_dev_xfmrs) > 0
                else None,
            },
        }

        # Transformer tap ratio analysis
        taps = branch_array[:, 8]
        taps_xfmr = taps[is_xfmr]
        taps_xfmr = np.where(taps_xfmr == 0, 1.0, taps_xfmr)
        n_nonunity = int((taps_xfmr != 1.0).sum())
        results["details"]["transformer_tap_analysis"] = {
            "total_transformers": n_xfmr_class,
            "tap_eq_1": n_xfmr_class - n_nonunity,
            "tap_ne_1": n_nonunity,
            "tap_range": [round(float(taps_xfmr.min()), 4), round(float(taps_xfmr.max()), 4)],
            "note": (
                "PyPSA DCPF includes tap ratio in susceptance (b=1/(x*tap)) "
                "while MATPOWER DCPF ignores tap ratio (b=1/x). This causes "
                f"systematic deviations on {n_nonunity} branches with non-unity taps."
            ),
        }

        # ── 8. Power balance ────────────────────────────────────────────
        total_gen_mw = float(net.generators.p_set.sum())
        total_load_mw = float(net.loads.p_set.sum())
        results["details"]["power_balance"] = {
            "total_gen_mw_presolve": round(total_gen_mw, 3),
            "total_load_mw": round(total_load_mw, 3),
            "ref_total_gen_mw_postsolve": ref_summary["total_gen_mw"],
            "ref_total_load_mw": ref_summary["total_load_mw"],
        }

        # ── 9. Pass/fail determination ──────────────────────────────────
        bus_pass = buses_within_tol >= PASS_FRACTION
        branch_pass = branches_within_tol >= PASS_FRACTION

        results["details"]["pass_conditions"] = {
            "bus_angle_pass": bus_pass,
            "bus_angle_fraction": round(buses_within_tol, 6),
            "bus_angle_threshold": PASS_FRACTION,
            "branch_flow_pass": branch_pass,
            "branch_flow_fraction": round(branches_within_tol, 6),
            "branch_flow_threshold": PASS_FRACTION,
        }

        if bus_pass and branch_pass:
            results["status"] = "pass"
        else:
            results["status"] = "fail"
            if not bus_pass:
                results["errors"].append(
                    f"Bus angle tolerance not met: {buses_within_tol:.4%} within "
                    f"{VA_TOL_DEG} deg (need {PASS_FRACTION:.0%}). Root cause: PyPSA "
                    "DCPF uses a different transformer model (tap-dependent susceptance) "
                    "than MATPOWER, causing systematic angle deviations."
                )
            if not branch_pass:
                results["errors"].append(
                    f"Branch flow tolerance not met: {branches_within_tol:.4%} within "
                    f"tolerance (need {PASS_FRACTION:.0%}). Same root cause: transformer "
                    "susceptance includes tap ratio in PyPSA but not in MATPOWER."
                )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 3)

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
