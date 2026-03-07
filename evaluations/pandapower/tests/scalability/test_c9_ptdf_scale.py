"""
Test C-9: PTDF matrix computation at scale

Dimension: scalability
Network: MEDIUM (ACTIVSg10k, ~10000 buses)
Pass condition: PTDF matrix computed on MEDIUM network.
Tool: pandapower v3.4.0
"""

import json
import os
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.pypower.makePTDF import makePTDF


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute PTDF computation at scale and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network and run DCPF
        load_start = time.perf_counter()
        net = from_mpc(network_file, f_hz=60)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed

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
        results["details"]["ptdf_expected_shape"] = [n_branch, n_bus]
        results["details"]["ptdf_matrix_size_elements"] = n_branch * n_bus
        results["details"]["ptdf_matrix_size_mb"] = (n_branch * n_bus * 8) / (1024 * 1024)

        # 3. Find slack bus
        from pandapower.pypower.idx_bus import BUS_TYPE, REF

        ref_buses = np.where(bus[:, BUS_TYPE] == REF)[0]
        slack_bus_idx = int(ref_buses[0]) if len(ref_buses) > 0 else 0
        results["details"]["slack_bus_ppc_idx"] = slack_bus_idx

        # Memory before PTDF
        try:
            import resource

            mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except Exception:
            mem_before = None

        # 4. Compute PTDF matrix (timed)
        ptdf_start = time.perf_counter()
        PTDF = makePTDF(baseMVA, bus, branch, slack_bus_idx)
        ptdf_elapsed = time.perf_counter() - ptdf_start
        results["details"]["ptdf_compute_seconds"] = ptdf_elapsed

        # Memory after PTDF
        try:
            mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            results["details"]["peak_memory_mb"] = mem_after
            if mem_before is not None:
                results["details"]["memory_delta_mb"] = mem_after - mem_before
        except Exception:
            pass

        # CPU utilization
        try:
            cpu_times = os.times()
            results["details"]["cpu_user_seconds"] = cpu_times.user
            results["details"]["cpu_system_seconds"] = cpu_times.system
        except Exception:
            pass

        # 5. Verify dimensions
        assert PTDF.shape == (n_branch, n_bus), (
            f"PTDF shape {PTDF.shape} != expected ({n_branch}, {n_bus})"
        )
        results["details"]["dimensions_correct"] = True

        # 6. Matrix statistics
        nonzero_count = np.count_nonzero(PTDF)
        total_elements = PTDF.size
        results["details"]["matrix_density"] = float(nonzero_count / total_elements)
        results["details"]["nonzero_elements"] = int(nonzero_count)
        results["details"]["total_elements"] = int(total_elements)
        results["details"]["ptdf_min"] = float(np.min(PTDF))
        results["details"]["ptdf_max"] = float(np.max(PTDF))
        results["details"]["ptdf_mean"] = float(np.mean(PTDF))
        results["details"]["slack_column_all_zero"] = bool(
            np.allclose(PTDF[:, slack_bus_idx], 0, atol=1e-10)
        )

        # 7. Validate: predict flows from PTDF and compare to DCPF
        from pandapower.pypower.idx_brch import PF
        from pandapower.pypower.idx_bus import PD
        from pandapower.pypower.idx_gen import GEN_BUS
        from pandapower.pypower.idx_gen import PG as GEN_PG

        gen = ppc["gen"]
        Pbus_mw = np.zeros(n_bus)
        Pbus_mw -= bus[:, PD]
        for i in range(gen.shape[0]):
            bus_idx = int(gen[i, GEN_BUS])
            Pbus_mw[bus_idx] += gen[i, GEN_PG]

        Pbus_pu = Pbus_mw / baseMVA
        branch_flows_pu = ppc["branch"][:, PF] / baseMVA

        predicted_flows_pu = PTDF @ Pbus_pu
        flow_diff = np.abs(predicted_flows_pu - branch_flows_pu)
        max_diff = float(np.max(flow_diff))
        mean_diff = float(np.mean(flow_diff))

        results["details"]["max_flow_diff_pu"] = max_diff
        results["details"]["mean_flow_diff_pu"] = mean_diff
        results["details"]["flow_prediction_accurate"] = max_diff < 1e-4

        # 8. Check pass condition
        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
