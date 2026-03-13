"""
Test B-9: PTDF Extraction and Flow Prediction

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: PTDF matrix accessible via native API. Flow predictions match
  DCPF flows within 0.01 pu on all branches (after excluding phase-shifting
  branches, if any).
Tool: PyPSA 1.1.2

Note: IEEE 39-bus has NO phase-shifting transformers (SHIFT=0 in all branches).
No Pbusinj/Pfinj correction needed.

Bus ordering note: PTDF columns follow `sn.buses_o` order (slack bus first,
then pvpqs buses), NOT n.buses alphabetical order. The injection vector must
be assembled in this order for PTDF @ P_inj to give correct flows.
"""

import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
BASE_MVA = 100.0  # System base power (case39 uses 100 MVA base)


def load_network(network_file: str):
    """Load case39.m via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Extract PTDF matrix and validate flow predictions against DCPF flows.

    API sequence:
    1. n.determine_network_topology()
    2. sn = n.sub_networks.at['0', 'obj']
    3. sn.calculate_PTDF()
    4. PTDF = sn.PTDF  (branches x buses numpy array)
    5. Build P_inj in sn.buses_o order (PTDF column ordering)
    6. Predicted flows (pu) = PTDF @ (P_inj_mw / baseMVA)
    7. Compare vs actual flows from n.lines_t.p0 and n.transformers_t.p0

    Key finding: PTDF columns are in sn.buses_o order ([slack, pvpq_0, pvpq_1, ...]),
    not in n.buses alphabetical order.

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
        n = load_network(network_file)
        n.lpf()

        # 2. Build network topology (required before PTDF computation)
        n.determine_network_topology()

        # 3. Access sub_network object
        sn_key = n.sub_networks.index[0]  # '0' for fully connected network
        sn_obj = n.sub_networks.at[sn_key, "obj"]

        # 4. Compute PTDF matrix via native PyPSA API
        sn_obj.calculate_PTDF()
        PTDF = sn_obj.PTDF  # numpy array: (n_branches, n_buses)

        ptdf_shape = PTDF.shape
        results["details"]["ptdf_shape"] = list(ptdf_shape)
        results["details"]["ptdf_dtype"] = str(PTDF.dtype)
        results["details"]["ptdf_min"] = float(PTDF.min())
        results["details"]["ptdf_max"] = float(PTDF.max())

        # 5. Get branch ordering: PTDF rows follow sn.branches_i() order
        #    (lines first, then transformers)
        branch_names = list(sn_obj.branches_i())
        n_branches = len(branch_names)

        assert ptdf_shape[0] == n_branches, (
            f"PTDF row count ({ptdf_shape[0]}) != n_branches ({n_branches})"
        )
        assert ptdf_shape[1] == len(n.buses), (
            f"PTDF col count ({ptdf_shape[1]}) != n_buses ({len(n.buses)})"
        )

        # 6. Get bus ordering for PTDF columns.
        #    CRITICAL: PTDF columns are in sn.buses_o order, NOT n.buses order.
        #    buses_o = [slack_bus, pvpq_0, pvpq_1, ...] (slack-first ordering)
        buses_o = list(sn_obj.buses_o)  # PTDF column order
        assert len(buses_o) == len(n.buses), (
            f"buses_o length ({len(buses_o)}) != n_buses ({len(n.buses)})"
        )

        # 7. Build injection vector in buses_o order
        #    n.buses_t.p contains net nodal injection (MW) = gen_dispatch - load
        p_bus_mw = n.buses_t.p.iloc[0]  # Series indexed by bus name
        P_inj_pu = np.array([p_bus_mw[b] / BASE_MVA for b in buses_o])

        # 8. Predicted flows = PTDF @ P_inj (result is in pu on BASE_MVA)
        predicted_flows_pu = PTDF @ P_inj_pu

        # 9. Actual flows from DCPF results (MW), converted to pu
        p0_lines = n.lines_t.p0.iloc[0]  # Series: line_name -> MW
        p0_xfmr = n.transformers_t.p0.iloc[0]  # Series: transformer_name -> MW

        actual_flows_pu = np.array(
            [
                (p0_lines[name] if ctype == "Line" else p0_xfmr[name]) / BASE_MVA
                for ctype, name in branch_names
            ]
        )

        # 10. Compute errors
        abs_diff_pu = np.abs(predicted_flows_pu - actual_flows_pu)
        max_abs_diff_pu = float(abs_diff_pu.max())
        mean_abs_diff_pu = float(abs_diff_pu.mean())
        n_within_tolerance = int((abs_diff_pu < 0.01).sum())

        results["details"]["n_branches_compared"] = n_branches
        results["details"]["max_abs_diff_pu"] = max_abs_diff_pu
        results["details"]["mean_abs_diff_pu"] = mean_abs_diff_pu
        results["details"]["n_within_0_01pu"] = n_within_tolerance
        results["details"]["tolerance_pu"] = 0.01
        results["details"]["slack_bus"] = sn_obj.slack_bus
        results["details"]["buses_o_first5"] = buses_o[:5]

        # Sample values for first 5 branches
        results["details"]["sample_flows"] = {}
        for i, (ctype, name) in enumerate(branch_names[:5]):
            results["details"]["sample_flows"][f"{ctype}:{name}"] = {
                "actual_pu": round(float(actual_flows_pu[i]), 6),
                "predicted_pu": round(float(predicted_flows_pu[i]), 6),
                "diff_pu": round(float(abs_diff_pu[i]), 6),
            }

        # PTDF sample: first row (first branch's sensitivity to all buses)
        first_ctype, first_name = branch_names[0]
        results["details"]["ptdf_first_row"] = {
            "branch": f"{first_ctype}:{first_name}",
            "max_abs_sensitivity": float(np.abs(PTDF[0, :]).max()),
            "n_nonzero": int((np.abs(PTDF[0, :]) > 1e-6).sum()),
        }

        # Pass condition: max_abs_diff < 0.01 pu on all branches
        pass_condition_met = max_abs_diff_pu < 0.01

        print(f"PTDF shape: {ptdf_shape} (branches x buses)")
        print(f"Slack bus: {sn_obj.slack_bus} (first in buses_o ordering)")
        print(f"Max |predicted - actual| flow: {max_abs_diff_pu:.2e} pu")
        print(f"Mean |predicted - actual| flow: {mean_abs_diff_pu:.2e} pu")
        print(f"Branches within 0.01 pu tolerance: {n_within_tolerance}/{n_branches}")
        print(f"Pass condition (max diff < 0.01 pu): {pass_condition_met}")

        if not pass_condition_met:
            worst_idx = int(np.argmax(abs_diff_pu))
            wctype, wname = branch_names[worst_idx]
            results["errors"].append(
                f"Max flow prediction error {max_abs_diff_pu:.6f} pu exceeds 0.01 pu tolerance "
                f"(worst: {wctype}:{wname})"
            )
            results["status"] = "fail"
        else:
            results["status"] = "pass"

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
