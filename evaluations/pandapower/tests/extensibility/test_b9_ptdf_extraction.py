"""
Test B-9: Compute PTDF matrix for TINY (39-bus). Verify dimensions and flow prediction.

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: PTDF matrix accessible via native API, internal matrix extraction,
    or unit-injection computation. Flow predictions match DCPF results within
    numerical tolerance (1e-6).
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.pypower.makePTDF import makePTDF


def run(network_file: str = "/workspace/data/networks/case39.m") -> dict:
    """Execute PTDF extraction test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network and run DCPF to populate internal structures
        net = from_mpc(network_file, f_hz=60)
        pp.rundcpp(net)
        assert net["converged"], "DCPF did not converge"

        # 2. Extract internal ppc arrays
        ppc = net._ppc
        baseMVA = ppc["baseMVA"]
        bus = ppc["bus"]
        branch = ppc["branch"]

        n_bus = bus.shape[0]
        n_branch = branch.shape[0]

        results["details"]["n_bus"] = n_bus
        results["details"]["n_branch"] = n_branch
        results["details"]["baseMVA"] = float(baseMVA)

        # 3. Identify slack bus (ref bus in ppc)
        from pandapower.pypower.idx_bus import BUS_TYPE, REF

        ref_buses = np.where(bus[:, BUS_TYPE] == REF)[0]
        slack_bus_idx = int(ref_buses[0]) if len(ref_buses) > 0 else 0
        results["details"]["slack_bus_ppc_idx"] = slack_bus_idx

        # 4. Compute PTDF matrix
        PTDF = makePTDF(baseMVA, bus, branch, slack_bus_idx)
        results["details"]["ptdf_shape"] = list(PTDF.shape)
        results["details"]["ptdf_expected_shape"] = [n_branch, n_bus]

        # Verify dimensions
        assert PTDF.shape == (n_branch, n_bus), (
            f"PTDF shape {PTDF.shape} != expected ({n_branch}, {n_bus})"
        )
        results["details"]["dimensions_correct"] = True

        # 5. Get DCPF-solved bus injections and branch flows
        from pandapower.pypower.idx_brch import PF
        from pandapower.pypower.idx_bus import PD
        from pandapower.pypower.idx_gen import GEN_BUS
        from pandapower.pypower.idx_gen import PG as GEN_PG

        # Build bus injection vector from gen and load data in ppc
        # bus[:,PD] has load (positive = consumption), gen has generation
        gen = ppc["gen"]
        Pbus_mw = np.zeros(n_bus)
        # Subtract loads
        Pbus_mw -= bus[:, PD]
        # Add generation
        for i in range(gen.shape[0]):
            bus_idx = int(gen[i, GEN_BUS])
            Pbus_mw[bus_idx] += gen[i, GEN_PG]

        Pbus_pu = Pbus_mw / baseMVA

        # Branch flows from DCPF solution (in MW)
        branch_flows_mw = ppc["branch"][:, PF]
        branch_flows_pu = branch_flows_mw / baseMVA

        # 6. Predict flows using PTDF
        predicted_flows_pu = PTDF @ Pbus_pu

        # 7. Compare predicted vs actual flows
        flow_diff = np.abs(predicted_flows_pu - branch_flows_pu)
        max_diff = float(np.max(flow_diff))
        mean_diff = float(np.mean(flow_diff))

        results["details"]["max_flow_diff_pu"] = max_diff
        results["details"]["mean_flow_diff_pu"] = mean_diff
        results["details"]["tolerance"] = 1e-6

        # Sample flows for documentation
        n_sample = min(10, n_branch)
        results["details"]["flow_comparison_sample"] = {
            "branch_idx": list(range(n_sample)),
            "dcpf_flow_mw": [float(branch_flows_mw[i]) for i in range(n_sample)],
            "ptdf_predicted_mw": [float(predicted_flows_pu[i] * baseMVA) for i in range(n_sample)],
            "diff_mw": [float(flow_diff[i] * baseMVA) for i in range(n_sample)],
        }

        # PTDF matrix statistics
        results["details"]["ptdf_stats"] = {
            "min": float(np.min(PTDF)),
            "max": float(np.max(PTDF)),
            "mean": float(np.mean(PTDF)),
            "nonzero_fraction": float(np.count_nonzero(PTDF) / PTDF.size),
            "slack_column_all_zero": bool(np.allclose(PTDF[:, slack_bus_idx], 0, atol=1e-10)),
        }

        # 8. Check pass condition
        if max_diff < 1e-6:
            results["status"] = "pass"
            results["details"]["match_quality"] = "exact (within 1e-6)"
        elif max_diff < 1e-4:
            results["status"] = "qualified_pass"
            results["details"]["match_quality"] = f"close (max diff = {max_diff:.2e})"
            results["workarounds"].append(
                f"PTDF flow prediction differs from DCPF by up to {max_diff:.2e} pu. "
                "This may be due to internal rounding or bus ordering differences."
            )
        else:
            results["errors"].append(
                f"PTDF flow prediction max diff = {max_diff:.2e} exceeds tolerance 1e-6"
            )

        # Document API access method
        results["details"]["api_access"] = (
            "PTDF via pandapower.pypower.makePTDF.makePTDF(baseMVA, bus, branch, slack). "
            "Requires extracting internal ppc arrays from net._ppc after rundcpp()."
        )
        results["details"]["access_level"] = (
            "Semi-internal: makePTDF is a public function in a public submodule, "
            "but input arrays come from net._ppc (underscore-prefixed internal attribute)."
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
