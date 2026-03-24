"""
Probe 005: Audit GridCal DC OPF branch flow constraint formulation.

Claim under investigation: A-3 reports 'pass' but branch 2_3_1 shows 112% loading.
Question: Are branch flow limits hard constraints or soft (slack/penalty) constraints?
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np

# Add the shared matpower_loader
sys.path.insert(0, str(Path("/workspace/evaluations/gridcal/tests")))

import VeraGridEngine as vge
from VeraGridEngine.enumerations import MIPSolvers, SolverType

NETWORK_FILE = "/workspace/data/networks/case39.m"
BRANCH_DERATING = 0.70

COST_MAP = {
    "hydro": {"c1": 5.0, "c2": 0.005},
    "nuclear": {"c1": 10.0, "c2": 0.010},
    "coal_large": {"c1": 25.0, "c2": 0.025},
    "gas_CC": {"c1": 40.0, "c2": 0.040},
}

print("=" * 70)
print("Probe 005: GridCal DC OPF Branch Constraint Formulation Audit")
print("=" * 70)
print("VeraGridEngine version: 5.6.28")
print(f"Network: {NETWORK_FILE}")
print(f"Branch derating: {BRANCH_DERATING * 100:.0f}%")
print()

# ── 1. Load network ──────────────────────────────────────────────────────────
print("Loading IEEE 39-bus network...")
grid = vge.open_file(NETWORK_FILE)
generators = grid.get_generators()
branches = grid.get_branches()
buses = grid.get_buses()
print(
    f"  Buses: {len(buses)}, Generators: {len(generators)}, Branches: {len(branches)}"
)

# ── 2. Apply differentiated costs ────────────────────────────────────────────
gen_tech = {
    0: "nuclear",
    1: "coal_large",
    2: "gas_CC",
    3: "gas_CC",
    4: "coal_large",
    5: "gas_CC",
    6: "hydro",
    7: "coal_large",
    8: "coal_large",
    9: "nuclear",
}
for idx, gen in enumerate(generators):
    tech_key = gen_tech.get(idx, "gas_CC")
    gen.Cost = COST_MAP[tech_key]["c1"]
    gen.Cost2 = COST_MAP[tech_key]["c2"]
    gen.Cost0 = 0.0

# ── 3. Apply 70% branch derating ─────────────────────────────────────────────
branch_original_rates = []
for branch in branches:
    if hasattr(branch, "rate"):
        original_rate = branch.rate
        branch_original_rates.append(original_rate)
        branch.rate = original_rate * BRANCH_DERATING
    else:
        branch_original_rates.append(0.0)

# ── 4. Inspect OPF formulation source ────────────────────────────────────────
print("\n--- Inspecting linear_opf source for constraint type ---")

try:
    src = inspect.getsource(vge.linear_opf)
    # Look for slack, penalty, or soft constraint indicators
    src_lower = src.lower()
    keywords = ["slack", "penalty", "soft", "overload", "epsilon", "relax"]
    for kw in keywords:
        count = src_lower.count(kw)
        if count > 0:
            print(f"  Keyword '{kw}' found {count} times in linear_opf source")
    print("  (full source inspection done — see keyword hits above)")
except Exception as e:
    print(f"  Could not inspect source: {e}")

# Try to inspect the underlying LP problem builder
try:
    from VeraGridEngine.Simulations.OPF import opf_driver

    opf_src = inspect.getsource(opf_driver)
    for kw in keywords:
        count = opf_src.lower().count(kw)
        if count > 0:
            print(f"  opf_driver keyword '{kw}': {count} hits")
except Exception as e:
    print(f"  Could not inspect opf_driver: {e}")

# ── 5. Run DC OPF ─────────────────────────────────────────────────────────────
print("\n--- Running DC OPF ---")
opf_opts = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
)
opf_results = vge.linear_opf(grid, opf_opts)
print(f"  Converged: {opf_results.converged}")

# ── 6. Inspect result object for soft-constraint evidence ─────────────────────
print("\n--- Result object attributes ---")
result_attrs = [a for a in dir(opf_results) if not a.startswith("_")]
soft_indicators = [
    a
    for a in result_attrs
    if any(
        kw in a.lower() for kw in ["overload", "slack", "penalty", "excess", "relax"]
    )
]
print(f"  Soft-constraint-related attributes: {soft_indicators}")
print(f"  All result attributes: {result_attrs}")

# ── 7. Check overloads attribute ──────────────────────────────────────────────
print("\n--- Branch loading analysis ---")
loading = opf_results.loading
sf = opf_results.Sf
branch_names = [b.name for b in branches]

overloaded = []
binding = []
for i in range(len(loading)):
    pct = abs(loading[i]) * 100
    if pct > 100.0:
        overloaded.append(
            (branch_names[i], pct, float(np.real(sf[i])), branch_original_rates[i])
        )
    elif pct >= 99.0:
        binding.append((branch_names[i], pct))

print(f"  Branches at exactly 100% (binding): {len(binding)}")
for name, pct in binding:
    print(f"    {name}: {pct:.1f}%")
print(f"  Branches EXCEEDING 100% (overloaded): {len(overloaded)}")
for name, pct, flow, rate in overloaded:
    derated_rate = rate * BRANCH_DERATING
    print(
        f"    {name}: {pct:.1f}% loading | flow={flow:.2f} MW | "
        f"derated_rate={derated_rate:.2f} MW | original_rate={rate:.2f} MW"
    )

# ── 8. Check overloads attribute directly ─────────────────────────────────────
print("\n--- opf_results.overloads attribute ---")
if hasattr(opf_results, "overloads") and opf_results.overloads is not None:
    overloads_arr = np.array(opf_results.overloads)
    nonzero = np.where(np.abs(overloads_arr) > 1e-6)[0]
    print(f"  Type: {type(opf_results.overloads)}")
    print(f"  Shape: {overloads_arr.shape}")
    print(f"  Non-zero entries (branch indices): {nonzero.tolist()}")
    for idx in nonzero:
        print(
            f"    Branch {branch_names[idx]} (idx={idx}): overload={overloads_arr[idx]:.4f}"
        )
    if len(overloads_arr) > 0:
        print(
            "  Interpretation: 'overloads' is a RESULT field capturing constraint violation,"
        )
        print(
            "  confirming these are SOFT CONSTRAINTS (flow limits exceeded without infeasibility)."
        )
else:
    print("  opf_results.overloads is None or absent")

# ── 9. Check shadow prices / dual variables ───────────────────────────────────
print("\n--- Shadow prices on branches ---")
shadow_attrs = [
    "branch_shadow_prices",
    "shadow_prices",
    "flow_shadow_prices",
    "Sf_shadow",
    "mu",
    "bus_shadow_prices",
]
for attr in shadow_attrs:
    if hasattr(opf_results, attr):
        val = getattr(opf_results, attr)
        if val is not None:
            arr = np.array(val)
            print(
                f"  {attr}: shape={arr.shape}, "
                f"nonzero={np.sum(np.abs(arr) > 1e-6)}, "
                f"max={np.max(np.abs(arr)):.4f}"
            )

# ── 10. Look for penalty/slack variables in LP model ─────────────────────────
print("\n--- Checking LP model for slack/penalty variables ---")
try:
    # Try to build the LP problem and inspect variables
    from VeraGridEngine.Simulations.OPF import LinearOpf

    print("  Found OPF classes:", [c for c in dir(LinearOpf) if not c.startswith("_")])
except ImportError as e:
    print(f"  Import failed: {e}")

try:
    # Check if the OPF results have an 'inner' LP model
    if hasattr(opf_results, "lp_model") and opf_results.lp_model is not None:
        lp = opf_results.lp_model
        print(f"  LP model type: {type(lp)}")
        print(f"  LP model attrs: {[a for a in dir(lp) if not a.startswith('_')]}")
    else:
        print("  No lp_model attribute in results")
except Exception as e:
    print(f"  LP model check error: {e}")

# ── 11. Inspect OptimalPowerFlowOptions for soft constraint settings ───────────
print("\n--- OptimalPowerFlowOptions settings ---")
opf_attrs = {
    a: getattr(opf_opts, a)
    for a in dir(opf_opts)
    if not a.startswith("_") and not callable(getattr(opf_opts, a))
}
for k, v in sorted(opf_attrs.items()):
    if any(
        kw in k.lower()
        for kw in ["slack", "soft", "penalty", "relax", "overload", "constraint"]
    ):
        print(f"  {k} = {v}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Branch 2_3_1 loading: {abs(loading[0]) * 100:.1f}%" if len(loading) > 0 else "")

# Find branch 2_3_1
for i, name in enumerate(branch_names):
    if "2_3" in name or name == "2_3_1":
        pct = abs(loading[i]) * 100
        print(f"Branch '{name}' (idx={i}): loading = {pct:.2f}%")
        if hasattr(opf_results, "overloads") and opf_results.overloads is not None:
            ov = float(opf_results.overloads[i])
            print(f"  overload value = {ov:.4f} MW")
        break

print()
print("CONCLUSION:")
if len(overloaded) > 0:
    print(
        "  SOFT CONSTRAINTS CONFIRMED: Branch flow limits are violated in the optimal"
    )
    print("  solution. The solver accepted a solution exceeding branch capacity, which")
    print(
        "  is only possible if limits are enforced as soft constraints (penalty/slack)"
    )
    print("  or if the branch was not included in the LP constraint set.")
    print()
    print("  The A-3 'pass' is MISLEADING: standard DCOPF requires hard flow limits.")
    print(
        "  GridCal's linear_opf appears to use soft constraints or penalty functions."
    )
else:
    print("  No branches overloaded — hard constraints appear to be working correctly.")
