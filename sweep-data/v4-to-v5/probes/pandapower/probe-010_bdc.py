# ruff: noqa: E402
"""
Probe 010 supplemental: Check makeBdc injection vectors and PTDF formulation.
"""

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.pypower.idx_bus import BUS_I, BUS_TYPE, REF
from pandapower.pypower.idx_brch import PF, TAP, F_BUS, T_BUS

net = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)
pp.rundcpp(net)
ppc = net._ppc
baseMVA = ppc["baseMVA"]
bus = ppc["bus"]
branch = ppc["branch"]

# Check makeBdc signature
import inspect
from pandapower.pypower.makeBdc import makeBdc

sig = inspect.signature(makeBdc)
print(f"makeBdc signature: {sig}")

# Try calling with proper args
try:
    result = makeBdc(baseMVA, bus, branch)
    print(f"makeBdc returned {len(result)} items")
    for i, item in enumerate(result):
        if hasattr(item, "shape"):
            print(f"  [{i}] shape={item.shape}, type={type(item).__name__}")
        elif hasattr(item, "toarray"):
            arr = item.toarray()
            print(
                f"  [{i}] sparse shape={arr.shape}, nnz={item.nnz}, type={type(item).__name__}"
            )
        else:
            print(f"  [{i}] type={type(item).__name__}, value={item}")
except Exception as e:
    print(f"makeBdc error: {e}")
    import traceback

    traceback.print_exc()

# Try alternative: check what DCPF solver uses internally
# The key insight: standard DC power flow solves:
#   P = B * theta + Pinj
# where Pinj accounts for tap ratios and phase shifters
# But PTDF = Bf * inv(Bbus) only gives the B*theta part
# The Pinj correction is missing from PTDF predictions

# Let's compute flows from bus angles directly
from pandapower.pypower.idx_bus import VA
from pandapower.pypower.idx_brch import BR_X

print("\n--- Flow computation from angles ---")
theta = bus[:, VA] * np.pi / 180  # Bus angles in radians

tap_ratios = branch[:, TAP].copy()
# In PYPOWER, tap=0 means tap=1.0
tap_ratios[tap_ratios == 0] = 1.0

is_trafo = tap_ratios != 1.0

# DC flow formula: Pf = (theta_f - theta_t) / x for lines
#                  Pf = (theta_f/tap - theta_t) / x  for transformers (approximate)
# But the exact PYPOWER DC formulation uses:
#   Bf(k) = -1/x(k) for both f and t sides
#   With tap: the B matrix entries are modified

n_branch = branch.shape[0]
from_bus_idx = branch[:, F_BUS].astype(int)
to_bus_idx = branch[:, T_BUS].astype(int)
x = branch[:, BR_X]

# Simple flow: P = (theta_f - theta_t) / x  (ignoring taps)
simple_flow = (theta[from_bus_idx] - theta[to_bus_idx]) / x

# Tap-corrected flow: P = (theta_f / tap - theta_t) / x
tap_corrected_flow = (theta[from_bus_idx] / tap_ratios - theta[to_bus_idx]) / x

dcpf_flow = branch[:, PF] / baseMVA

diff_simple = np.abs(simple_flow - dcpf_flow)
diff_corrected = np.abs(tap_corrected_flow - dcpf_flow)

print("\nSimple flow (no tap correction):")
print(f"  Max diff from DCPF: {np.max(diff_simple):.6f} pu")
print(f"  Mean diff: {np.mean(diff_simple):.6f} pu")

print("\nTap-corrected flow:")
print(f"  Max diff from DCPF: {np.max(diff_corrected):.6f} pu")
print(f"  Mean diff: {np.mean(diff_corrected):.6f} pu")

# Which formula does DCPF actually use?
# Check on transformer branches only
print(f"\nOn transformer branches only ({np.sum(is_trafo)}):")
print(f"  Simple: max diff = {np.max(diff_simple[is_trafo]):.6f}")
print(f"  Corrected: max diff = {np.max(diff_corrected[is_trafo]):.6f}")

print(f"\nOn line branches only ({np.sum(~is_trafo)}):")
print(f"  Simple: max diff = {np.max(diff_simple[~is_trafo]):.6f}")
print(f"  Corrected: max diff = {np.max(diff_corrected[~is_trafo]):.6f}")

# Now check: does PTDF use bus angles or something else?
# PTDF predicts flow from injections: P_flow = PTDF @ P_inj
# The DCPF solver gets theta from: Bbus @ theta = P_inj - Pbusinj
# Then computes flow from: P_flow = Bf @ theta + Pfinj
# If PTDF ignores Pbusinj and Pfinj, the error comes from those terms

# Let's check: does the PTDF flow differ from simple angle-based flow?
from pandapower.pypower.makePTDF import makePTDF
from pandapower.pypower.idx_gen import GEN_BUS, GEN_STATUS, PG as GEN_PG
from pandapower.pypower.idx_bus import PD

ref_buses = np.where(bus[:, BUS_TYPE] == REF)[0]
slack_idx = int(ref_buses[0])
PTDF = makePTDF(baseMVA, bus, branch, slack_idx)

# Build injection
n_bus = bus.shape[0]
ext_to_int = {int(bus[i, BUS_I]): i for i in range(n_bus)}
Pbus_mw = -bus[:, PD].copy()
gen = ppc["gen"]
for i in range(gen.shape[0]):
    if gen[i, GEN_STATUS] > 0:
        int_idx = ext_to_int.get(int(gen[i, GEN_BUS]), -1)
        if int_idx >= 0:
            Pbus_mw[int_idx] += gen[i, GEN_PG]
Pbus_pu = Pbus_mw / baseMVA

ptdf_flow = PTDF @ Pbus_pu

# Compare PTDF flow to simple (no-tap) angle flow and tap-corrected
print("\n--- PTDF vs angle-based flows ---")
diff_ptdf_simple = np.abs(ptdf_flow - simple_flow)
diff_ptdf_corrected = np.abs(ptdf_flow - tap_corrected_flow)
diff_ptdf_dcpf = np.abs(ptdf_flow - dcpf_flow)

print(f"PTDF vs simple flow:  max diff = {np.max(diff_ptdf_simple):.6f}")
print(f"PTDF vs corrected:    max diff = {np.max(diff_ptdf_corrected):.6f}")
print(f"PTDF vs DCPF flow:    max diff = {np.max(diff_ptdf_dcpf):.6f}")

# The key question: does PTDF = simple flow (no taps)?
# If so, the error is entirely tap-related
if np.max(diff_ptdf_simple) < 1e-6:
    print("\n** PTDF matches simple (no-tap) flow exactly! **")
    print("** Error is ENTIRELY due to tap ratio effects **")
elif np.max(diff_ptdf_corrected) < 1e-6:
    print("\n** PTDF matches tap-corrected flow exactly! **")
    print("** PTDF DOES account for taps; error is from something else **")
else:
    print("\n** PTDF differs from both simple and corrected flows **")
    print("** The relationship is more complex **")

# Check: does the error come from Pbusinj (tap-induced injection shift)?
# In DC power flow with taps, the flow equation is:
#   Bf @ theta + Pfinj = actual_flow
# And the bus balance is:
#   Bbus @ theta = Pinj - Pbusinj
# So theta = inv(Bbus) @ (Pinj - Pbusinj)
# And flow = Bf @ inv(Bbus) @ (Pinj - Pbusinj) + Pfinj
#          = PTDF @ Pinj - PTDF @ Pbusinj + Pfinj
# But makePTDF gives: PTDF @ Pinj
# The missing terms are: -PTDF @ Pbusinj + Pfinj

# Let's try to compute Pbusinj and Pfinj
print("\n--- Computing tap injection corrections ---")
# Phase shift angle for each branch (in the PYPOWER convention)
from pandapower.pypower.idx_brch import SHIFT

shift = branch[:, SHIFT] * np.pi / 180  # convert to radians

# For DC power flow, Pfinj = -b * shift (for phase shifters)
# and Pbusinj comes from the bus injection due to tap/shift
b = 1.0 / x  # branch susceptance magnitude

# Pfinj = -b * (-shift) = b * shift (depends on PYPOWER convention)
# Actually let's just check if shift is nonzero
print(f"Branches with nonzero shift angle: {np.sum(np.abs(shift) > 1e-10)}")
print(f"Max |shift|: {np.max(np.abs(shift)):.6f} rad")

print("\nConclusion: The error is propagated through the network topology.")
print("Tap ratios change the B-matrix entries, which changes theta at all buses,")
print("which changes flow on all branches — not just transformer branches.")
