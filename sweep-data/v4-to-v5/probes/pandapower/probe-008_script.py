"""
Probe 008: Verify PTDF flow divergence claim on ACTIVSg10k.

Claim: "PTDF flow predictions diverge from DCPF on MEDIUM (max diff 7.43 pu)
but test still passes"

Approach:
1. Load ACTIVSg10k and solve DCPF
2. Compute PTDF matrix via makePTDF
3. Build injection vector from solved ppc
4. Compare PTDF-predicted flows to DCPF actual flows
5. Also test on case39 (TINY) as a baseline
"""

import json
import time

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.pypower.makePTDF import makePTDF
from pandapower.pypower.idx_bus import BUS_I, BUS_TYPE, GS, PD, REF
from pandapower.pypower.idx_brch import PF
from pandapower.pypower.idx_gen import GEN_BUS, GEN_STATUS, PG as GEN_PG

start = time.perf_counter()
results = {}


def test_ptdf(network_file, label):
    """Test PTDF accuracy on a given network."""
    r = {}
    try:
        net = from_mpc(network_file, f_hz=60)
        pp.rundcpp(net)
        assert net["converged"], "DCPF did not converge"

        ppc = net._ppc
        baseMVA = ppc["baseMVA"]
        bus = ppc["bus"]
        branch = ppc["branch"]
        gen = ppc["gen"]

        n_bus = bus.shape[0]
        n_branch = branch.shape[0]

        r["n_bus"] = n_bus
        r["n_branch"] = n_branch
        r["baseMVA"] = float(baseMVA)

        # Slack bus
        ref_buses = np.where(bus[:, BUS_TYPE] == REF)[0]
        slack_bus_idx = int(ref_buses[0]) if len(ref_buses) > 0 else 0
        r["slack_bus_idx"] = slack_bus_idx

        # Compute PTDF
        ptdf_start = time.perf_counter()
        PTDF = makePTDF(baseMVA, bus, branch, slack_bus_idx)
        ptdf_time = time.perf_counter() - ptdf_start
        r["ptdf_seconds"] = round(ptdf_time, 3)
        r["ptdf_shape"] = list(PTDF.shape)
        r["ptdf_memory_mb"] = round(PTDF.nbytes / (1024 * 1024), 2)

        # Build bus injection vector
        ext_to_int = {}
        for i in range(n_bus):
            ext_to_int[int(bus[i, BUS_I])] = i

        Pbus_mw = np.zeros(n_bus)
        Pbus_mw -= bus[:, PD]  # subtract loads

        if bus.shape[1] > GS:
            Pbus_mw -= bus[:, GS]  # subtract shunts

        for i in range(gen.shape[0]):
            if gen[i, GEN_STATUS] > 0:
                ext_bus = int(gen[i, GEN_BUS])
                int_idx = ext_to_int.get(ext_bus, -1)
                if int_idx >= 0:
                    Pbus_mw[int_idx] += gen[i, GEN_PG]

        Pbus_pu = Pbus_mw / baseMVA

        # Actual DCPF flows
        branch_flows_pu = branch[:, PF] / baseMVA

        # PTDF-predicted flows
        predicted_flows_pu = PTDF @ Pbus_pu

        # Differences
        flow_diff = np.abs(predicted_flows_pu - branch_flows_pu)
        r["max_diff_pu"] = round(float(np.max(flow_diff)), 6)
        r["mean_diff_pu"] = round(float(np.mean(flow_diff)), 6)
        r["median_diff_pu"] = round(float(np.median(flow_diff)), 6)
        r["max_diff_mw"] = round(float(np.max(flow_diff) * baseMVA), 4)

        # Where are the big differences?
        worst_indices = np.argsort(flow_diff)[-5:][::-1]
        r["worst_5_branches"] = []
        for idx in worst_indices:
            r["worst_5_branches"].append(
                {
                    "branch_idx": int(idx),
                    "dcpf_flow_pu": round(float(branch_flows_pu[idx]), 6),
                    "ptdf_flow_pu": round(float(predicted_flows_pu[idx]), 6),
                    "diff_pu": round(float(flow_diff[idx]), 6),
                }
            )

        # Check injection balance
        r["total_injection_mw"] = round(float(Pbus_mw.sum()), 4)
        r["total_gen_mw"] = round(float(gen[gen[:, GEN_STATUS] > 0, GEN_PG].sum()), 4)
        r["total_load_mw"] = round(float(bus[:, PD].sum()), 4)
        r["total_shunt_mw"] = (
            round(float(bus[:, GS].sum()), 4) if bus.shape[1] > GS else 0
        )

        # Slack column check
        r["slack_col_all_zero"] = bool(
            np.allclose(PTDF[:, slack_bus_idx], 0, atol=1e-10)
        )

        # Check if shunts are causing the divergence
        # Test without shunt subtraction
        Pbus_no_shunt_mw = np.zeros(n_bus)
        Pbus_no_shunt_mw -= bus[:, PD]
        for i in range(gen.shape[0]):
            if gen[i, GEN_STATUS] > 0:
                ext_bus = int(gen[i, GEN_BUS])
                int_idx = ext_to_int.get(ext_bus, -1)
                if int_idx >= 0:
                    Pbus_no_shunt_mw[int_idx] += gen[i, GEN_PG]
        Pbus_no_shunt_pu = Pbus_no_shunt_mw / baseMVA
        predicted_no_shunt_pu = PTDF @ Pbus_no_shunt_pu
        diff_no_shunt = np.abs(predicted_no_shunt_pu - branch_flows_pu)
        r["max_diff_no_shunt_pu"] = round(float(np.max(diff_no_shunt)), 6)
        r["mean_diff_no_shunt_pu"] = round(float(np.mean(diff_no_shunt)), 6)

    except Exception as e:
        r["error"] = f"{type(e).__name__}: {e}"
        import traceback

        r["traceback"] = traceback.format_exc()

    return r


# Test on TINY first (baseline)
results["case39"] = test_ptdf("/workspace/data/networks/case39.m", "TINY")

# Test on MEDIUM
results["case10k"] = test_ptdf("/workspace/data/networks/case_ACTIVSg10k.m", "MEDIUM")

results["wall_clock_seconds"] = round(time.perf_counter() - start, 2)
print(json.dumps(results, indent=2, default=str))
