"""
Test B-9: PTDF Extraction and Flow Prediction

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: PTDF matrix accessible via native API. Flow predictions match
  DCPF flows within 0.01 pu on all non-phase-shifting branches.
  Record PTDF build time and matrix shape.
Tool: PyPSA 1.1.2

Note: ACTIVSg10k has 5 phase-shifting transformers. Per cross-tool watchpoints,
the full correction formula is: flow = PTDF @ (Pinj - Pbusinj) + Pfinj.
Phase-shifting branches are excluded from the accuracy comparison, or the
correction terms are applied.
"""

import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")
BASE_MVA = 100.0


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc dict -> pypsa."""
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
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Extract PTDF matrix and validate flow predictions on 10k-bus network.

    Records PTDF build time and matrix shape.
    Accounts for phase-shifting transformers per cross-tool watchpoints.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
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
        # 1. Load network and run DCPF
        print("Loading 10k network...")
        n = load_network(network_file)
        print(
            f"Loaded: {len(n.buses)} buses, {len(n.lines)} lines, {len(n.transformers)} transformers"
        )

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)

        print("Running DCPF...")
        t_lpf_start = time.perf_counter()
        n.lpf()
        t_lpf_elapsed = time.perf_counter() - t_lpf_start
        print(f"DCPF done in {t_lpf_elapsed:.2f}s")
        results["details"]["lpf_seconds"] = t_lpf_elapsed

        # 2. Build network topology
        print("Computing network topology...")
        n.determine_network_topology()

        # 3. Access sub_network object
        sn_key = n.sub_networks.index[0]
        sn_obj = n.sub_networks.at[sn_key, "obj"]

        # 4. Compute PTDF matrix via native PyPSA API
        print("Computing PTDF matrix...")
        t_ptdf_start = time.perf_counter()
        sn_obj.calculate_PTDF()
        PTDF = sn_obj.PTDF
        t_ptdf_elapsed = time.perf_counter() - t_ptdf_start
        print(f"PTDF built in {t_ptdf_elapsed:.4f}s, shape={PTDF.shape}")

        ptdf_shape = PTDF.shape
        results["details"]["ptdf_shape"] = list(ptdf_shape)
        results["details"]["ptdf_dtype"] = str(PTDF.dtype)
        results["details"]["ptdf_min"] = float(PTDF.min())
        results["details"]["ptdf_max"] = float(PTDF.max())
        results["details"]["ptdf_build_seconds"] = t_ptdf_elapsed

        # 5. Get branch and bus ordering
        branch_names = list(sn_obj.branches_i())
        n_branches = len(branch_names)
        buses_o = list(sn_obj.buses_o)

        assert ptdf_shape[0] == n_branches, (
            f"PTDF rows ({ptdf_shape[0]}) != n_branches ({n_branches})"
        )
        assert ptdf_shape[1] == len(n.buses), (
            f"PTDF cols ({ptdf_shape[1]}) != n_buses ({len(n.buses)})"
        )

        results["details"]["slack_bus"] = str(sn_obj.slack_bus)
        results["details"]["buses_o_first5"] = buses_o[:5]

        # 6. Build injection vector in buses_o order
        p_bus_mw = n.buses_t.p.iloc[0]
        P_inj_pu = np.array([p_bus_mw[b] / BASE_MVA for b in buses_o])

        # 7. Apply shift corrections for transformers with off-nominal taps and phase shifts.
        #
        # ACTIVSg10k has 970 off-nominal-tap transformers and 5 phase-shifting transformers.
        # The simple formula PTDF @ P_inj is inaccurate on such networks.
        # PyPSA exposes p_bus_shift and p_branch_shift correction vectors (in MW):
        #   flow_pu = PTDF @ (P_inj_pu - p_bus_shift/BASE_MVA) + p_branch_shift/BASE_MVA
        #
        # This is the full correction formula from cross-tool-watchpoints.md:
        #   flow = PTDF @ (Pinj - Pbusinj) + Pfinj
        # where Pbusinj = p_bus_shift/BASE_MVA and Pfinj = p_branch_shift/BASE_MVA.
        p_bus_shift = sn_obj.p_bus_shift  # numpy array in MW (buses_o order)
        p_branch_shift = sn_obj.p_branch_shift  # numpy array in MW (branches_i order)

        n_p_bus_shift_nonzero = int((np.abs(p_bus_shift) > 1e-8).sum())
        n_p_branch_shift_nonzero = int((np.abs(p_branch_shift) > 1e-8).sum())
        print(f"p_bus_shift nonzero entries: {n_p_bus_shift_nonzero}")
        print(f"p_branch_shift nonzero entries: {n_p_branch_shift_nonzero}")

        # Simple formula (no correction) — for comparison
        predicted_simple_pu = PTDF @ P_inj_pu

        # Corrected formula — applies tap+phase-shift corrections
        predicted_flows_pu = PTDF @ (P_inj_pu - p_bus_shift / BASE_MVA) + p_branch_shift / BASE_MVA

        results["details"]["n_p_bus_shift_nonzero"] = n_p_bus_shift_nonzero
        results["details"]["n_p_branch_shift_nonzero"] = n_p_branch_shift_nonzero
        results["details"]["correction_applied"] = True
        results["details"]["correction_method"] = (
            "flow_pu = PTDF @ (P_inj_pu - p_bus_shift/BASE_MVA) + p_branch_shift/BASE_MVA"
        )

        # 8. Actual flows from DCPF
        p0_lines = n.lines_t.p0.iloc[0]
        p0_xfmr = n.transformers_t.p0.iloc[0]

        actual_flows_pu = np.array(
            [
                (p0_lines[name] if ctype == "Line" else p0_xfmr[name]) / BASE_MVA
                for ctype, name in branch_names
            ]
        )

        # 9. Check for phase-shifting transformers (for documentation)
        phase_shift_branches = set()
        if len(n.transformers) > 0 and "phase_shift" in n.transformers.columns:
            ps_xfmrs = n.transformers[np.abs(n.transformers["phase_shift"]) > 1e-6]
            for xfmr_name in ps_xfmrs.index:
                phase_shift_branches.add(("Transformer", xfmr_name))
            print(f"Phase-shifting transformers: {len(ps_xfmrs)} found")

        # Also check off-nominal tap transformers
        n_off_nominal_tap = 0
        if len(n.transformers) > 0 and "tap_ratio" in n.transformers.columns:
            off_tap = n.transformers[np.abs(n.transformers["tap_ratio"] - 1.0) > 1e-4]
            n_off_nominal_tap = len(off_tap)
            print(f"Off-nominal-tap transformers: {n_off_nominal_tap}")

        n_phase_shift = len(phase_shift_branches)
        print(f"Phase-shifting branches: {n_phase_shift}")
        results["details"]["n_phase_shift_branches"] = n_phase_shift
        results["details"]["n_off_nominal_tap_transformers"] = n_off_nominal_tap

        # 10. Compute errors with corrected formula
        abs_diff_pu = np.abs(predicted_flows_pu - actual_flows_pu)
        abs_diff_simple_pu = np.abs(predicted_simple_pu - actual_flows_pu)

        max_abs_diff_all = float(abs_diff_pu.max())
        mean_abs_diff_all = float(abs_diff_pu.mean())
        n_within_tolerance = int((abs_diff_pu < 0.01).sum())
        n_non_ps = len(branch_names)

        # For reporting, also show simple formula performance
        results["details"]["simple_formula_max_diff_pu"] = float(abs_diff_simple_pu.max())
        results["details"]["simple_formula_within_0_01"] = int((abs_diff_simple_pu < 0.01).sum())

        # Non-PS mask (all branches since correction handles both tap and phase shift)
        non_ps_mask = np.ones(len(branch_names), dtype=bool)
        abs_diff_non_ps = abs_diff_pu  # all branches
        max_abs_diff_non_ps = max_abs_diff_all
        mean_abs_diff_non_ps = mean_abs_diff_all

        print(f"Max |pred-actual| (all branches): {max_abs_diff_all:.4f} pu")
        print(f"Max |pred-actual| (non-PS branches): {max_abs_diff_non_ps:.4f} pu")
        print(f"Branches within 0.01 pu (non-PS): {n_within_tolerance}/{n_non_ps}")

        results["details"]["n_branches_compared"] = n_branches
        results["details"]["n_non_ps_branches"] = n_non_ps
        results["details"]["max_abs_diff_all_pu"] = max_abs_diff_all
        results["details"]["mean_abs_diff_all_pu"] = mean_abs_diff_all
        results["details"]["max_abs_diff_non_ps_pu"] = max_abs_diff_non_ps
        results["details"]["mean_abs_diff_non_ps_pu"] = mean_abs_diff_non_ps
        results["details"]["n_within_0_01pu_non_ps"] = n_within_tolerance
        results["details"]["tolerance_pu"] = 0.01

        # Sample: first 5 branches
        results["details"]["sample_flows"] = {}
        for i, (ctype, name) in enumerate(branch_names[:5]):
            results["details"]["sample_flows"][f"{ctype}:{name}"] = {
                "actual_pu": round(float(actual_flows_pu[i]), 6),
                "predicted_pu": round(float(predicted_flows_pu[i]), 6),
                "diff_pu": round(float(abs_diff_pu[i]), 6),
            }

        # PTDF sample: first row
        first_ctype, first_name = branch_names[0]
        results["details"]["ptdf_first_row"] = {
            "branch": f"{first_ctype}:{first_name}",
            "max_abs_sensitivity": float(np.abs(PTDF[0, :]).max()),
            "n_nonzero": int((np.abs(PTDF[0, :]) > 1e-6).sum()),
        }

        # Pass condition: max_abs_diff < 0.01 pu on non-PS branches
        pass_condition_met = max_abs_diff_non_ps < 0.01

        errors = []
        if not pass_condition_met:
            worst_non_ps_idx = int(np.argmax(abs_diff_non_ps))
            non_ps_names = [branch_names[i] for i in range(n_branches) if non_ps_mask[i]]
            if worst_non_ps_idx < len(non_ps_names):
                wctype, wname = non_ps_names[worst_non_ps_idx]
                errors.append(
                    f"Max flow prediction error {max_abs_diff_non_ps:.6f} pu exceeds 0.01 pu "
                    f"on non-PS branches (worst: {wctype}:{wname})"
                )
            else:
                errors.append(
                    f"Max flow prediction error {max_abs_diff_non_ps:.6f} pu exceeds 0.01 pu tolerance"
                )

        results["errors"].extend(errors)
        if not errors:
            results["status"] = "pass"
        else:
            results["status"] = "fail"

        print(f"Pass condition (non-PS branches within 0.01 pu): {pass_condition_met}")

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
