"""
Test B-9: Compute the PTDF matrix for TINY (39-bus) and verify against DCPF

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: PTDF matrix accessible via native API, internal matrix extraction, or
  unit-injection computation. Flow predictions match DCPF results within numerical
  tolerance (1e-6). If the network contains phase-shifting transformers (nonzero SHIFT
  column in branch data), the PTDF validation must either (a) apply Pbusinj/Pfinj
  correction terms from the admittance matrix construction, or (b) exclude branches
  with nonzero shift angles from the accuracy comparison. The 1e-6 tolerance applies
  to the corrected or filtered comparison.
Tool: PyPSA 1.1.2

Note: IEEE 39-bus has NO phase-shifting transformers (SHIFT=0 on all branches).
No Pbusinj/Pfinj correction needed. The 1e-6 tolerance applies directly.

Bus ordering: PTDF columns follow sn.buses_o order (slack bus first, then pvpqs),
NOT n.buses alphabetical order. The injection vector must be assembled in this order.
"""

import sys
import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
BASE_MVA = 100.0
TOLERANCE = 1e-6  # Per pass condition


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Extract PTDF matrix and validate flow predictions against DCPF.

    API sequence:
    1. Load network via shared loader
    2. Run DCPF: n.lpf()
    3. Build topology: n.determine_network_topology()
    4. Compute PTDF: sn.calculate_PTDF()
    5. Extract PTDF matrix: sn.PTDF (branches x buses numpy array)
    6. Build P_inj in sn.buses_o order (PTDF column ordering)
    7. Predicted flows (pu) = PTDF @ P_inj_pu
    8. Compare vs actual DCPF flows within 1e-6 tolerance

    Returns:
        dict with standard result keys.
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
        from matpower_loader import load_pypsa

        # 1. Load network
        n = load_pypsa(network_file)

        # 2. Check for phase-shifting transformers
        from matpowercaseframes import CaseFrames

        cf = CaseFrames(network_file)
        branch_data = cf.branch
        # SHIFT column is column index 9 (0-based) in MATPOWER branch format
        if branch_data.shape[1] > 9:
            shift_col = branch_data.iloc[:, 9]
            has_phase_shifters = (shift_col.abs() > 1e-10).any()
            n_phase_shifters = int((shift_col.abs() > 1e-10).sum())
        else:
            has_phase_shifters = False
            n_phase_shifters = 0

        results["details"]["has_phase_shifters"] = has_phase_shifters
        results["details"]["n_phase_shifters"] = n_phase_shifters

        # 3. Run DCPF
        n.lpf()

        # 4. Build network topology
        n.determine_network_topology()
        sn_key = n.sub_networks.index[0]
        sn_obj = n.sub_networks.at[sn_key, "obj"]

        # 5. Compute PTDF via native API
        sn_obj.calculate_PTDF()
        PTDF = sn_obj.PTDF

        ptdf_shape = PTDF.shape
        results["details"]["ptdf_shape"] = list(ptdf_shape)
        results["details"]["ptdf_dtype"] = str(PTDF.dtype)
        results["details"]["ptdf_min"] = round(float(PTDF.min()), 8)
        results["details"]["ptdf_max"] = round(float(PTDF.max()), 8)
        results["details"]["ptdf_api"] = "sub_network.calculate_PTDF() -> sub_network.PTDF"

        # 6. Get branch ordering (PTDF rows = sn.branches_i() order)
        branch_names = list(sn_obj.branches_i())
        n_branches = len(branch_names)
        n_buses = len(n.buses)

        assert ptdf_shape[0] == n_branches, (
            f"PTDF rows ({ptdf_shape[0]}) != n_branches ({n_branches})"
        )
        assert ptdf_shape[1] == n_buses, f"PTDF cols ({ptdf_shape[1]}) != n_buses ({n_buses})"

        # 7. Get bus ordering for PTDF columns
        # CRITICAL: PTDF columns are in sn.buses_o order, NOT n.buses alphabetical order
        buses_o = list(sn_obj.buses_o)
        slack_bus = sn_obj.slack_bus
        results["details"]["slack_bus"] = str(slack_bus)
        results["details"]["buses_o_first5"] = buses_o[:5]
        results["details"]["n_branches"] = n_branches
        results["details"]["n_buses"] = n_buses

        # 8. Build injection vector in buses_o order
        p_bus_mw = n.buses_t.p.iloc[0]  # Net nodal injection (MW)
        P_inj_pu = np.array([p_bus_mw[b] / BASE_MVA for b in buses_o])

        # 9. Predicted flows = PTDF @ P_inj_pu
        predicted_flows_pu = PTDF @ P_inj_pu

        # 10. Actual flows from DCPF (MW -> pu)
        p0_lines = n.lines_t.p0.iloc[0]
        p0_xfmr = n.transformers_t.p0.iloc[0]

        actual_flows_pu = np.array(
            [
                (p0_lines[name] if ctype == "Line" else p0_xfmr[name]) / BASE_MVA
                for ctype, name in branch_names
            ]
        )

        # 11. Compute errors
        abs_diff = np.abs(predicted_flows_pu - actual_flows_pu)
        max_abs_diff = float(abs_diff.max())
        mean_abs_diff = float(abs_diff.mean())
        n_within_tolerance = int((abs_diff < TOLERANCE).sum())

        results["details"]["max_abs_diff_pu"] = max_abs_diff
        results["details"]["mean_abs_diff_pu"] = mean_abs_diff
        results["details"]["n_within_tolerance"] = n_within_tolerance
        results["details"]["tolerance"] = TOLERANCE

        # Per-branch comparison for first 10 branches
        results["details"]["branch_comparison"] = []
        for i, (ctype, name) in enumerate(branch_names[:10]):
            results["details"]["branch_comparison"].append(
                {
                    "branch": f"{ctype}:{name}",
                    "actual_pu": round(float(actual_flows_pu[i]), 8),
                    "predicted_pu": round(float(predicted_flows_pu[i]), 8),
                    "diff_pu": float(abs_diff[i]),
                }
            )

        # Worst branch
        worst_idx = int(np.argmax(abs_diff))
        wctype, wname = branch_names[worst_idx]
        results["details"]["worst_branch"] = {
            "branch": f"{wctype}:{wname}",
            "actual_pu": round(float(actual_flows_pu[worst_idx]), 8),
            "predicted_pu": round(float(predicted_flows_pu[worst_idx]), 8),
            "diff_pu": float(abs_diff[worst_idx]),
        }

        # PTDF row statistics
        results["details"]["ptdf_row_stats"] = {
            "mean_abs_sensitivity": round(float(np.abs(PTDF).mean()), 6),
            "max_abs_sensitivity": round(float(np.abs(PTDF).max()), 6),
            "sparsity_pct": round(float((np.abs(PTDF) < 1e-10).sum()) / PTDF.size * 100, 1),
        }

        print(f"PTDF shape: {ptdf_shape}")
        print(f"Slack bus: {slack_bus}")
        print(f"Phase shifters: {n_phase_shifters}")
        print(f"Max |predicted - actual|: {max_abs_diff:.2e} (tolerance: {TOLERANCE:.0e})")
        print(f"Mean |predicted - actual|: {mean_abs_diff:.2e}")
        print(f"Branches within tolerance: {n_within_tolerance}/{n_branches}")

        # 12. Pass condition: all branches within 1e-6
        if has_phase_shifters:
            # Filter out phase-shifting branches from comparison
            # (Not applicable for case39, but included for correctness)
            print("Phase shifters present — would filter from comparison")

        pass_condition_met = max_abs_diff < TOLERANCE
        results["details"]["pass_condition_met"] = pass_condition_met

        if pass_condition_met:
            results["status"] = "pass"
            print(f"PASS: All flows within {TOLERANCE:.0e} tolerance")
        else:
            results["status"] = "fail"
            results["errors"].append(
                f"Max flow prediction error {max_abs_diff:.2e} exceeds {TOLERANCE:.0e} tolerance "
                f"(worst: {wctype}:{wname})"
            )
            print(f"FAIL: Max error {max_abs_diff:.2e} exceeds tolerance")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
