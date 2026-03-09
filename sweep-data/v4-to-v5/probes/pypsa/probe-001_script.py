"""Probe 001: Verify ACPF convergence on ACTIVSg10k network.

Checks whether PyPSA's Newton-Raphson AC power flow actually converges
on the 10k-bus network, what the solver status says, and what residuals look like.
"""

import time
import warnings
import sys

import pypsa
import numpy as np
from matpowercaseframes import CaseFrames

print(f"PyPSA version: {pypsa.__version__}")

# Load network from MATPOWER case file
network_path = "/workspace/data/networks/case_ACTIVSg10k.m"
print(f"Loading network from {network_path}...")
t0 = time.perf_counter()

cf = CaseFrames(network_path)
ppc = {
    "version": "2",
    "baseMVA": cf.baseMVA,
    "bus": cf.bus.values,
    "gen": cf.gen.values,
    "branch": cf.branch.values,
}

n = pypsa.Network()
n.import_from_pypower_ppc(ppc)

load_time = time.perf_counter() - t0
print(f"Network load time: {load_time:.2f}s")
print(f"Buses: {len(n.buses)}")
print(f"Lines: {len(n.lines)}")
print(f"Transformers: {len(n.transformers)}")
print(f"Generators: {len(n.generators)}")

# Run Newton-Raphson AC power flow, capturing warnings
print("\nRunning Newton-Raphson AC power flow...")
captured_warnings = []
t0 = time.perf_counter()

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        result = n.pf()
        pf_time = time.perf_counter() - t0
        captured_warnings = [str(warning.message) for warning in w]
    except Exception as e:
        pf_time = time.perf_counter() - t0
        print(f"EXCEPTION during pf(): {type(e).__name__}: {e}")
        sys.exit(1)

print(f"Power flow solve time: {pf_time:.2f}s")

# Check convergence status
print("\n=== CONVERGENCE STATUS ===")
print(f"Result type: {type(result)}")

if isinstance(result, dict):
    for key, val in result.items():
        if hasattr(val, "to_dict"):
            print(f"  {key}: {val.to_dict()}")
        else:
            print(f"  {key}: {val}")
elif isinstance(result, tuple):
    for i, val in enumerate(result):
        print(f"  result[{i}]: {val}")
else:
    print(f"  result: {result}")

# Check warnings
print("\n=== WARNINGS ===")
if captured_warnings:
    for w_msg in captured_warnings:
        print(f"  WARNING: {w_msg}")
else:
    print("  No warnings captured")

# Analyze voltage magnitudes
print("\n=== VOLTAGE ANALYSIS ===")
v_mag = n.buses_t.v_mag_pu
if not v_mag.empty:
    v_vals = v_mag.values.flatten()
    v_vals = v_vals[~np.isnan(v_vals)]
    print(f"V magnitude range: {v_vals.min():.4f} - {v_vals.max():.4f} pu")
    print(f"V magnitude mean: {v_vals.mean():.4f} pu")
    print(f"V magnitude std: {v_vals.std():.6f} pu")
    print(f"Buses with V < 0.9: {(v_vals < 0.9).sum()}")
    print(f"Buses with V > 1.1: {(v_vals > 1.1).sum()}")
    print(f"Buses with V == 1.0 (flat start unchanged): {(v_vals == 1.0).sum()}")
    # Check if all voltages are exactly 1.0 (flat start never updated)
    all_flat = np.allclose(v_vals, 1.0)
    print(f"All voltages at flat start (1.0): {all_flat}")
else:
    print("No voltage magnitude results available")

# Analyze power flows
print("\n=== LINE FLOW ANALYSIS ===")
p0 = n.lines_t.p0
if not p0.empty:
    p_vals = p0.values.flatten()
    p_vals = p_vals[~np.isnan(p_vals)]
    print(f"Line p0 range: {p_vals.min():.1f} - {p_vals.max():.1f} MW")
    print(f"Line p0 mean abs: {np.abs(p_vals).mean():.1f} MW")
    print(f"Lines with zero flow: {(p_vals == 0.0).sum()}")
else:
    print("No line flow results available")

# Check transformer flows
print("\n=== TRANSFORMER FLOW ANALYSIS ===")
tp0 = n.transformers_t.p0
if not tp0.empty:
    tp_vals = tp0.values.flatten()
    tp_vals = tp_vals[~np.isnan(tp_vals)]
    print(f"Transformer p0 range: {tp_vals.min():.1f} - {tp_vals.max():.1f} MW")
    print(f"Transformer p0 mean abs: {np.abs(tp_vals).mean():.1f} MW")
else:
    print("No transformer flow results available")

# Compute power balance residuals
print("\n=== POWER BALANCE CHECK ===")
try:
    gen_p = n.generators_t.p
    if not gen_p.empty:
        total_gen = gen_p.values.sum()
        print(f"Total generation: {total_gen:.1f} MW")

    if hasattr(n, "loads") and len(n.loads) > 0:
        if not n.loads_t.p.empty:
            total_load = n.loads_t.p.values.sum()
        else:
            total_load = n.loads.p_set.sum()
        print(f"Total load: {total_load:.1f} MW")

    if not p0.empty:
        line_p1 = n.lines_t.p1.values.sum() if not n.lines_t.p1.empty else 0
        line_losses = p0.values.sum() + line_p1
        print(f"Line losses (p0+p1): {line_losses:.1f} MW")

    if not tp0.empty:
        trafo_p1 = (
            n.transformers_t.p1.values.sum() if not n.transformers_t.p1.empty else 0
        )
        trafo_losses = tp0.values.sum() + trafo_p1
        print(f"Transformer losses (p0+p1): {trafo_losses:.1f} MW")
except Exception as e:
    print(f"Error computing power balance: {e}")

print(f"\nTotal wall clock: {load_time + pf_time:.2f}s")
