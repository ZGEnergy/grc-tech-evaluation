"""D-4: Error quality tests for PyPSA accessibility evaluation."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"


def load_network(case_file: str = "case39.m"):
    cf = CaseFrames(str(DATA_DIR / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net, cf


results = {}

# --- Test (a): Infeasible OPF — set a line limit to 0 ---
print("=" * 60)
print("TEST (a): Infeasible OPF — set line limit to 0")
print("=" * 60)
try:
    net, cf = load_network()
    # Assign costs so OPF has a valid objective
    gencost = cf.gencost.values
    for i, gen_name in enumerate(net.generators.index):
        if i < len(gencost):
            c1 = gencost[i, 5]
            net.generators.at[gen_name, "marginal_cost"] = c1

    # Set ALL line limits to 0 to force infeasibility
    net.lines["s_nom"] = 0.0
    net.transformers["s_nom"] = 0.0

    status = net.optimize(solver_name="highs")
    print(f"Solver returned status: {status}")
    print(f"Objective: {net.objective}")

    # Check if any generation happened
    gen_p = net.generators_t.p
    print(f"Generator dispatch:\n{gen_p}")

    results["a"] = {
        "status": str(status),
        "objective": float(net.objective) if hasattr(net, "objective") else None,
        "error": None,
    }
except Exception as e:
    tb = traceback.format_exc()
    print(f"Exception: {type(e).__name__}: {e}")
    print(tb)
    results["a"] = {
        "status": "exception",
        "error": f"{type(e).__name__}: {e}",
        "traceback": tb,
    }

# --- Test (b): Missing generator cost curve ---
print("\n" + "=" * 60)
print("TEST (b): Missing generator cost curve (all costs = 0)")
print("=" * 60)
try:
    net, cf = load_network()
    # Do NOT assign any costs — leave marginal_cost at default (0.0)
    print(f"Generator marginal_cost values: {net.generators['marginal_cost'].tolist()}")

    status = net.optimize(solver_name="highs")
    print(f"Solver returned status: {status}")
    print(f"Objective: {net.objective}")

    gen_p = net.generators_t.p
    print(f"Generator dispatch sum: {gen_p.iloc[0].sum() if len(gen_p) > 0 else 'N/A'}")

    results["b"] = {
        "status": str(status),
        "objective": float(net.objective) if hasattr(net, "objective") else None,
        "error": None,
    }
except Exception as e:
    tb = traceback.format_exc()
    print(f"Exception: {type(e).__name__}: {e}")
    print(tb)
    results["b"] = {
        "status": "exception",
        "error": f"{type(e).__name__}: {e}",
        "traceback": tb,
    }

# --- Test (c): Invalid bus type ---
print("\n" + "=" * 60)
print("TEST (c): Invalid bus type — with power flow")
print("=" * 60)
try:
    net, cf = load_network()
    # Try setting a bus control type to an invalid value
    print(f"Bus control types before: {net.buses['control'].unique().tolist()}")

    # Set bus control to an invalid type
    first_bus = net.buses.index[0]
    net.buses.at[first_bus, "control"] = "InvalidType"
    print(f"Set bus '{first_bus}' control to 'InvalidType'")
    print(f"Bus control types after: {net.buses['control'].unique().tolist()}")

    # Try running power flow with invalid bus type
    convergence = net.pf()
    print(f"PF convergence info: {convergence}")

    results["c_pf"] = {
        "status": "completed_without_error",
        "error": None,
    }
except Exception as e:
    tb = traceback.format_exc()
    print(f"Exception: {type(e).__name__}: {e}")
    print(tb)
    results["c_pf"] = {
        "status": "exception",
        "error": f"{type(e).__name__}: {e}",
        "traceback": tb,
    }

# Also try invalid bus type with optimize
print("\n--- Test (c) variant: Invalid bus type with optimize ---")
try:
    net, cf = load_network()
    # Assign costs for valid OPF
    gencost = cf.gencost.values
    for i, gen_name in enumerate(net.generators.index):
        if i < len(gencost):
            c1 = gencost[i, 5]
            net.generators.at[gen_name, "marginal_cost"] = c1

    # Set a bus to a completely invalid type string
    first_bus = net.buses.index[0]
    net.buses.at[first_bus, "control"] = "BOGUS_TYPE_999"
    print(f"Set bus '{first_bus}' control to 'BOGUS_TYPE_999'")

    status = net.optimize(solver_name="highs")
    print(f"Solver returned status: {status}")

    results["c_opf"] = {
        "status": str(status),
        "error": None,
    }
except Exception as e:
    tb = traceback.format_exc()
    print(f"Exception: {type(e).__name__}: {e}")
    print(tb)
    results["c_opf"] = {
        "status": "exception",
        "error": f"{type(e).__name__}: {e}",
        "traceback": tb,
    }

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(json.dumps(results, indent=2, default=str))
