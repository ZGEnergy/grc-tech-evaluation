"""
Probe 010 final: Verify that PTDF error is explained by missing Pbusinj/Pfinj terms.
"""

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.pypower.idx_bus import BUS_I, BUS_TYPE, PD, REF
from pandapower.pypower.idx_brch import PF
from pandapower.pypower.idx_gen import GEN_BUS, GEN_STATUS, PG as GEN_PG
from pandapower.pypower.makePTDF import makePTDF
from pandapower.pypower.makeBdc import makeBdc

net = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)
pp.rundcpp(net)
ppc = net._ppc
baseMVA = ppc["baseMVA"]
bus = ppc["bus"]
branch = ppc["branch"]
gen = ppc["gen"]
n_bus = bus.shape[0]
n_branch = branch.shape[0]

# Get PTDF
ref_buses = np.where(bus[:, BUS_TYPE] == REF)[0]
slack_idx = int(ref_buses[0])
PTDF = makePTDF(baseMVA, bus, branch, slack_idx)

# Get Bbus, Bf, and the extra terms from makeBdc
bdc_result = makeBdc(bus, branch)
print(f"makeBdc returned {len(bdc_result)} values")
for i, v in enumerate(bdc_result):
    if hasattr(v, "shape"):
        print(f"  [{i}] shape={v.shape}")
    elif hasattr(v, "toarray"):
        print(f"  [{i}] sparse, shape={v.toarray().shape}")
    else:
        print(f"  [{i}] type={type(v).__name__}")

Bbus = bdc_result[0]
Bf = bdc_result[1]
# Check what other values are returned
extra = bdc_result[2:]
print(f"\nExtra return values: {len(extra)}")

# Build injection vector
ext_to_int = {int(bus[i, BUS_I]): i for i in range(n_bus)}
Pbus_mw = -bus[:, PD].copy()
for i in range(gen.shape[0]):
    if gen[i, GEN_STATUS] > 0:
        int_idx = ext_to_int.get(int(gen[i, GEN_BUS]), -1)
        if int_idx >= 0:
            Pbus_mw[int_idx] += gen[i, GEN_PG]
Pbus_pu = Pbus_mw / baseMVA

dcpf_flow = branch[:, PF] / baseMVA
ptdf_flow = PTDF @ Pbus_pu

# Check each extra return value
for i, v in enumerate(extra):
    if hasattr(v, "toarray"):
        arr = v.toarray().flatten()
    elif hasattr(v, "shape"):
        arr = v.flatten()
    else:
        continue
    nnz = np.sum(np.abs(arr) > 1e-10)
    print(
        f"  extra[{i}]: shape={arr.shape}, nnz={nnz}, max|v|={np.max(np.abs(arr)):.6f}"
    )

# The makeBdc in pandapower 3.4.0 may return (Bbus, Bf, Pbusinj, Pfinj)
# or different. Let's try to use the extra terms to correct PTDF prediction
if len(extra) >= 2:
    Pbusinj = extra[0]
    Pfinj = extra[1]
    if hasattr(Pbusinj, "toarray"):
        Pbusinj = Pbusinj.toarray().flatten()
    elif hasattr(Pbusinj, "flatten"):
        Pbusinj = Pbusinj.flatten()
    if hasattr(Pfinj, "toarray"):
        Pfinj = Pfinj.toarray().flatten()
    elif hasattr(Pfinj, "flatten"):
        Pfinj = Pfinj.flatten()

    print(
        f"\nPbusinj: shape={Pbusinj.shape}, nnz={np.sum(np.abs(Pbusinj) > 1e-10)}, max={np.max(np.abs(Pbusinj)):.6f}"
    )
    print(
        f"Pfinj: shape={Pfinj.shape}, nnz={np.sum(np.abs(Pfinj) > 1e-10)}, max={np.max(np.abs(Pfinj)):.6f}"
    )

    # Corrected flow = PTDF @ (Pinj - Pbusinj) + Pfinj
    corrected_flow = PTDF @ (Pbus_pu - Pbusinj) + Pfinj

    diff_original = np.abs(ptdf_flow - dcpf_flow)
    diff_corrected = np.abs(corrected_flow - dcpf_flow)

    print("\n--- Correction Results ---")
    print(
        f"Original PTDF error:   max={np.max(diff_original):.6f} pu, mean={np.mean(diff_original):.6f} pu"
    )
    print(
        f"Corrected PTDF error:  max={np.max(diff_corrected):.6f} pu, mean={np.mean(diff_corrected):.6f} pu"
    )
    print(
        f"Improvement ratio:     {np.max(diff_original) / np.max(diff_corrected):.1f}x (max), {np.mean(diff_original) / np.mean(diff_corrected):.1f}x (mean)"
    )

    if np.max(diff_corrected) < 1e-6:
        print("\n** Correction eliminates ALL error! **")
        print(
            "** The PTDF is correct but needs Pbusinj/Pfinj adjustment for tap ratios **"
        )
    elif np.max(diff_corrected) < np.max(diff_original) * 0.01:
        print("\n** Correction eliminates >99% of error **")
    else:
        print("\n** Correction reduces error but doesn't eliminate it **")
        # Try just Pbusinj correction
        corr_pbusinj_only = PTDF @ (Pbus_pu - Pbusinj)
        diff_pbusinj = np.abs(corr_pbusinj_only - dcpf_flow)
        print(f"  Pbusinj only: max={np.max(diff_pbusinj):.6f}")
        # Try just Pfinj correction
        corr_pfinj_only = ptdf_flow + Pfinj
        diff_pfinj = np.abs(corr_pfinj_only - dcpf_flow)
        print(f"  Pfinj only:   max={np.max(diff_pfinj):.6f}")
elif len(extra) >= 1:
    Pbusinj = extra[0]
    if hasattr(Pbusinj, "toarray"):
        Pbusinj = Pbusinj.toarray().flatten()
    elif hasattr(Pbusinj, "flatten"):
        Pbusinj = Pbusinj.flatten()
    print(f"\nOnly Pbusinj available: shape={Pbusinj.shape}")
    corrected = PTDF @ (Pbus_pu - Pbusinj)
    diff_corrected = np.abs(corrected - dcpf_flow)
    print(
        f"Corrected error: max={np.max(diff_corrected):.6f}, mean={np.mean(diff_corrected):.6f}"
    )
else:
    print("\nNo extra terms from makeBdc — cannot compute correction")
