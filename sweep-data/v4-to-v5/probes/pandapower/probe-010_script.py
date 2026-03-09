# ruff: noqa: E402
"""
Probe 010: PTDF error attribution — transformer tap ratios vs other factors.

Context from probe-008: The 7.43 pu max diff is real and confirmed. Shunts are 0 MW.
This probe investigates whether the error concentrates on transformer branches
and whether tap ratio correction resolves it.
"""

import time
import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc

start_time = time.perf_counter()

print("=" * 60)
print("PROBE 010: PTDF error attribution — transformers vs other factors")
print("=" * 60)

# 1. Load and solve DCPF
print("\n--- Loading ACTIVSg10k ---")
net = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)
pp.rundcpp(net)
assert net["converged"], "DCPF did not converge"

# 2. Extract ppc internals
ppc = net._ppc
baseMVA = ppc["baseMVA"]
bus = ppc["bus"]
branch = ppc["branch"]
gen = ppc["gen"]

n_bus = bus.shape[0]
n_branch = branch.shape[0]

from pandapower.pypower.idx_bus import BUS_I, BUS_TYPE, PD, REF
from pandapower.pypower.idx_brch import PF, TAP, F_BUS, T_BUS
from pandapower.pypower.idx_gen import GEN_BUS, GEN_STATUS, PG as GEN_PG

# 3. Identify transformer branches (tap != 0 and tap != 1.0)
tap_ratios = branch[:, TAP]
is_trafo = (tap_ratios != 0.0) & (tap_ratios != 1.0)
n_trafo = np.sum(is_trafo)
n_line = n_branch - n_trafo

print(f"Total branches: {n_branch}")
print(f"Transformer branches (tap != 0 and != 1): {n_trafo}")
print(f"Line branches: {n_line}")

# Tap ratio statistics for transformers
trafo_taps = tap_ratios[is_trafo]
print("\nTransformer tap ratio stats:")
print(f"  Min: {np.min(trafo_taps):.6f}")
print(f"  Max: {np.max(trafo_taps):.6f}")
print(f"  Mean: {np.mean(trafo_taps):.6f}")
print(f"  Std: {np.std(trafo_taps):.6f}")
print(f"  # with tap != 1.0: {np.sum(trafo_taps != 1.0)}")

# 4. Compute PTDF and flow predictions
from pandapower.pypower.makePTDF import makePTDF

ref_buses = np.where(bus[:, BUS_TYPE] == REF)[0]
slack_bus_idx = int(ref_buses[0])

PTDF = makePTDF(baseMVA, bus, branch, slack_bus_idx)

# Build injection vector
ext_to_int = {}
for i in range(n_bus):
    ext_to_int[int(bus[i, BUS_I])] = i

Pbus_mw = np.zeros(n_bus)
Pbus_mw -= bus[:, PD]

for i in range(gen.shape[0]):
    if gen[i, GEN_STATUS] > 0:
        ext_bus = int(gen[i, GEN_BUS])
        int_idx = ext_to_int.get(ext_bus, -1)
        if int_idx >= 0:
            Pbus_mw[int_idx] += gen[i, GEN_PG]

Pbus_pu = Pbus_mw / baseMVA

# DCPF flows and PTDF predicted flows
dcpf_flows_pu = branch[:, PF] / baseMVA
ptdf_flows_pu = PTDF @ Pbus_pu

flow_diff = np.abs(ptdf_flows_pu - dcpf_flows_pu)
max_diff = float(np.max(flow_diff))
mean_diff = float(np.mean(flow_diff))

print("\n--- Overall Flow Error ---")
print(f"Max diff: {max_diff:.4f} pu ({max_diff * baseMVA:.2f} MW)")
print(f"Mean diff: {mean_diff:.6f} pu ({mean_diff * baseMVA:.2f} MW)")

# 5. Error by branch type
trafo_diffs = flow_diff[is_trafo]
line_diffs = flow_diff[~is_trafo]

print("\n--- Error by Branch Type ---")
print(f"Transformer branches ({n_trafo}):")
print(
    f"  Max diff: {np.max(trafo_diffs):.4f} pu ({np.max(trafo_diffs) * baseMVA:.2f} MW)"
)
print(
    f"  Mean diff: {np.mean(trafo_diffs):.6f} pu ({np.mean(trafo_diffs) * baseMVA:.2f} MW)"
)
print(f"  Median diff: {np.median(trafo_diffs):.6f} pu")
print(f"  # with diff > 0.01 pu: {np.sum(trafo_diffs > 0.01)}")
print(f"  # with diff > 0.1 pu: {np.sum(trafo_diffs > 0.1)}")
print(f"  # with diff > 1.0 pu: {np.sum(trafo_diffs > 1.0)}")

print(f"\nLine branches ({n_line}):")
print(
    f"  Max diff: {np.max(line_diffs):.4f} pu ({np.max(line_diffs) * baseMVA:.2f} MW)"
)
print(
    f"  Mean diff: {np.mean(line_diffs):.6f} pu ({np.mean(line_diffs) * baseMVA:.2f} MW)"
)
print(f"  Median diff: {np.median(line_diffs):.6f} pu")
print(f"  # with diff > 0.01 pu: {np.sum(line_diffs > 0.01)}")
print(f"  # with diff > 0.1 pu: {np.sum(line_diffs > 0.1)}")
print(f"  # with diff > 1.0 pu: {np.sum(line_diffs > 1.0)}")

# 6. Top 10 worst branches — are they transformers?
worst_idx = np.argsort(flow_diff)[-20:][::-1]
print("\n--- Top 20 Worst Branches ---")
print(
    f"{'Rank':>4} {'Branch':>7} {'Type':>6} {'Tap':>8} {'DCPF(pu)':>10} {'PTDF(pu)':>10} {'Diff(pu)':>10}"
)
n_worst_trafo = 0
for rank, idx in enumerate(worst_idx):
    btype = "TRAFO" if is_trafo[idx] else "LINE"
    tap = tap_ratios[idx]
    if is_trafo[idx]:
        n_worst_trafo += 1
    print(
        f"{rank + 1:>4} {idx:>7} {btype:>6} {tap:>8.4f} {dcpf_flows_pu[idx]:>10.4f} {ptdf_flows_pu[idx]:>10.4f} {flow_diff[idx]:>10.4f}"
    )

print(
    f"\nOf top 20 worst: {n_worst_trafo} are transformers, {20 - n_worst_trafo} are lines"
)

# 7. Correlation between tap deviation and error for transformers
if n_trafo > 0:
    tap_deviation = np.abs(trafo_taps - 1.0)
    correlation = np.corrcoef(tap_deviation, trafo_diffs)[0, 1]
    print("\n--- Tap Deviation vs Error Correlation ---")
    print(f"Pearson correlation (|tap-1| vs error): {correlation:.4f}")

# 8. Total error contribution
total_error = float(np.sum(flow_diff))
trafo_error_total = float(np.sum(trafo_diffs))
line_error_total = float(np.sum(line_diffs))
print("\n--- Error Attribution ---")
print(f"Total absolute error: {total_error:.4f} pu")
print(
    f"Transformer contribution: {trafo_error_total:.4f} pu ({trafo_error_total / total_error * 100:.1f}%)"
)
print(
    f"Line contribution: {line_error_total:.4f} pu ({line_error_total / total_error * 100:.1f}%)"
)

# 9. Check: do lines with large errors connect to transformer buses?
# Hypothesis: lines adjacent to transformers may show error propagation
print("\n--- Error Propagation Check ---")
trafo_buses = set()
for i in range(n_branch):
    if is_trafo[i]:
        trafo_buses.add(int(branch[i, F_BUS]))
        trafo_buses.add(int(branch[i, T_BUS]))

line_indices = np.where(~is_trafo)[0]
line_adjacent_to_trafo = []
line_not_adjacent = []
for i in line_indices:
    fbus = int(branch[i, F_BUS])
    tbus = int(branch[i, T_BUS])
    if fbus in trafo_buses or tbus in trafo_buses:
        line_adjacent_to_trafo.append(i)
    else:
        line_not_adjacent.append(i)

adj_diffs = (
    flow_diff[line_adjacent_to_trafo] if line_adjacent_to_trafo else np.array([0])
)
nonadj_diffs = flow_diff[line_not_adjacent] if line_not_adjacent else np.array([0])

print(f"Lines adjacent to transformer buses: {len(line_adjacent_to_trafo)}")
print(f"  Mean error: {np.mean(adj_diffs):.6f} pu")
print(f"  Max error: {np.max(adj_diffs):.6f} pu")
print(f"Lines NOT adjacent to transformer buses: {len(line_not_adjacent)}")
print(f"  Mean error: {np.mean(nonadj_diffs):.6f} pu")
print(f"  Max error: {np.max(nonadj_diffs):.6f} pu")

# 10. Attempt PTDF with tap correction
# The standard PTDF uses Bf * inv(Bbus), where both use the same susceptance
# For transformers with tap t, the admittance matrix has asymmetric entries:
# Y_ff = y / t^2, Y_ft = -y / t, Y_tf = -y / t, Y_tt = y
# But the standard B matrix used in DC power flow should account for this.
# Let's check if makePTDF uses the same B matrix as the DCPF solver.
print("\n--- PTDF B-matrix Check ---")
from pandapower.pypower.makeBdc import makeBdc

# makeBdc should build Bbus and Bf accounting for taps
try:
    result = makeBdc(baseMVA, bus, branch)
    if len(result) == 4:
        Bbus, Bf, Pbusinj, Pfinj = result
    elif len(result) == 3:
        Bbus, Bf, Pbusinj = result
        Pfinj = None
    else:
        Bbus = result[0]
        Bf = result[1] if len(result) > 1 else None
        Pfinj = None

    print(f"makeBdc returned {len(result)} values")

    # Check if Pfinj (phase shift injection) is non-zero
    if Pfinj is not None:
        pfinj_arr = (
            np.array(Pfinj).flatten()
            if hasattr(Pfinj, "toarray")
            else np.array(Pfinj).flatten()
        )
        print(
            f"Pfinj (phase shift injection): max abs = {np.max(np.abs(pfinj_arr)):.6f}"
        )
        print(f"Pfinj nonzero count: {np.sum(np.abs(pfinj_arr) > 1e-10)}")

    if Pbusinj is not None:
        pbusinj_arr = (
            np.array(Pbusinj).flatten()
            if hasattr(Pbusinj, "toarray")
            else np.array(Pbusinj).flatten()
        )
        print(f"Pbusinj (bus injection): max abs = {np.max(np.abs(pbusinj_arr)):.6f}")
        print(f"Pbusinj nonzero count: {np.sum(np.abs(pbusinj_arr) > 1e-10)}")
        # The PTDF formulation doesn't account for Pbusinj/Pfinj corrections
        # These represent the phase-shifter and tap corrections that modify the
        # simple P = B * theta relationship to P = B * theta + Pinj
        print("\nThe Pbusinj vector represents fixed injections from tap ratios")
        print("that the PTDF formulation ignores. This is the likely error source.")

except Exception as e:
    print(f"makeBdc error: {e}")

elapsed = time.perf_counter() - start_time
print(f"\n--- Total elapsed: {elapsed:.2f}s ---")
