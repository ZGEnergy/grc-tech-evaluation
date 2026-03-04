"""
Test B-1: Add flow gate limit to DC OPF from A-3

Dimension: extensibility
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Achievable through documented API, no forking.
Tool: pypsa 1.1.2
Solver: HiGHS (LP)

A flow gate (interface) is a group of monitored lines with a combined transfer limit.
This test adds a flow gate constraint to the DC OPF using PyPSA's extra_functionality
callback, which provides access to the linopy model for custom constraints.
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"

# HiGHS solver settings
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300.0,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}


def _load_network(case_file: str) -> tuple[pypsa.Network, CaseFrames]:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
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


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute the test and return structured results."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    case_file = Path(network_file).name

    start = time.perf_counter()
    try:
        # 1. Load network and assign costs (same as A-3)
        net, cf = _load_network(case_file)

        gencost = cf.gencost.values
        for i, gen_name in enumerate(net.generators.index):
            if i < len(gencost):
                c2 = gencost[i, 4]
                c1 = gencost[i, 5]
                p_operating = net.generators.at[gen_name, "p_set"]
                marginal = c1 + 2 * c2 * p_operating
                net.generators.at[gen_name, "marginal_cost"] = marginal

        for gen_name in net.generators.index:
            if net.generators.at[gen_name, "p_nom"] <= 0:
                net.generators.at[gen_name, "p_nom"] = net.generators.at[gen_name, "p_set"] * 1.5

        # 2. First solve baseline DC OPF (without flow gate) for comparison
        baseline_status = net.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        baseline_objective = net.objective
        baseline_flows = net.lines_t.p0.iloc[0].copy()
        baseline_dispatch = net.generators_t.p.iloc[0].copy()

        results["details"]["baseline_objective"] = float(baseline_objective)
        results["details"]["baseline_status"] = str(baseline_status)

        # 3. Define a flow gate: group of lines with a combined transfer limit
        # Pick lines that carry significant flow in the baseline to make it interesting
        # Use lines connecting the generation-heavy area to the load area
        # Lines L2 (bus 3-4) and L3 (bus 3-18) form a natural interface
        gate_lines = []
        gate_directions = []  # +1 or -1 to define positive flow direction

        # Select 3 lines that form a meaningful interface
        line_list = list(net.lines.index)
        if len(line_list) >= 5:
            gate_lines = [line_list[2], line_list[3], line_list[4]]
            gate_directions = [1.0, 1.0, 1.0]
        else:
            gate_lines = line_list[: min(3, len(line_list))]
            gate_directions = [1.0] * len(gate_lines)

        # Calculate baseline gate flow
        baseline_gate_flow = sum(
            d * baseline_flows[ln] for ln, d in zip(gate_lines, gate_directions)
        )

        # Set gate limit to 80% of baseline flow to force re-dispatch
        gate_limit = abs(baseline_gate_flow) * 0.80

        results["details"]["gate_lines"] = gate_lines
        results["details"]["gate_directions"] = gate_directions
        results["details"]["baseline_gate_flow_mw"] = float(baseline_gate_flow)
        results["details"]["gate_limit_mw"] = float(gate_limit)

        # 4. Re-solve with flow gate constraint via extra_functionality
        # Reload network to clear previous solution
        net2, cf2 = _load_network(case_file)

        gencost2 = cf2.gencost.values
        for i, gen_name in enumerate(net2.generators.index):
            if i < len(gencost2):
                c2 = gencost2[i, 4]
                c1 = gencost2[i, 5]
                p_operating = net2.generators.at[gen_name, "p_set"]
                marginal = c1 + 2 * c2 * p_operating
                net2.generators.at[gen_name, "marginal_cost"] = marginal

        for gen_name in net2.generators.index:
            if net2.generators.at[gen_name, "p_nom"] <= 0:
                net2.generators.at[gen_name, "p_nom"] = net2.generators.at[gen_name, "p_set"] * 1.5

        def flow_gate_constraint(network, snapshots):
            """Add flow gate constraint: sum of directional flows <= gate_limit."""
            m = network.model

            # Line flow variables in PyPSA optimize: "Line-s" for DC OPF
            # The variable has dimensions (snapshot, name) where name = line names
            line_flow_var = m.variables["Line-s"]

            # Build gate flow expression: sum of direction * flow for gate lines
            gate_flow_terms = []
            for ln, direction in zip(gate_lines, gate_directions):
                if ln in line_flow_var.coords["name"].values:
                    flow = line_flow_var.sel(name=ln)
                    gate_flow_terms.append(direction * flow)

            if gate_flow_terms:
                gate_flow = gate_flow_terms[0]
                for term in gate_flow_terms[1:]:
                    gate_flow = gate_flow + term

                # Add upper bound: gate_flow <= gate_limit
                m.add_constraints(
                    gate_flow <= gate_limit,
                    name="flow_gate_upper",
                )
                # Add lower bound: gate_flow >= -gate_limit
                m.add_constraints(
                    gate_flow >= -gate_limit,
                    name="flow_gate_lower",
                )

        gate_status = net2.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
            extra_functionality=flow_gate_constraint,
        )

        gate_objective = net2.objective
        gate_flows = net2.lines_t.p0.iloc[0].copy()
        gate_dispatch = net2.generators_t.p.iloc[0].copy()

        # Calculate constrained gate flow
        constrained_gate_flow = sum(
            d * gate_flows[ln] for ln, d in zip(gate_lines, gate_directions)
        )

        results["details"]["gate_status"] = str(gate_status)
        results["details"]["gate_objective"] = float(gate_objective)
        results["details"]["constrained_gate_flow_mw"] = float(constrained_gate_flow)
        results["details"]["objective_increase_pct"] = float(
            (gate_objective - baseline_objective) / baseline_objective * 100
        )

        # Verify gate constraint is respected
        gate_respected = abs(constrained_gate_flow) <= gate_limit + 1e-6
        results["details"]["gate_constraint_respected"] = gate_respected

        # Dispatch changes
        dispatch_diff = gate_dispatch - baseline_dispatch
        results["details"]["dispatch_changes"] = {
            str(k): float(v) for k, v in dispatch_diff.items() if abs(v) > 0.1
        }

        # LMPs
        lmps = net2.buses_t.marginal_price
        if len(lmps) > 0:
            results["details"]["lmp_range"] = [
                float(lmps.iloc[0].min()),
                float(lmps.iloc[0].max()),
            ]

        # Shadow price on gate constraint
        if hasattr(net2.model, "constraints"):
            try:
                gate_dual = net2.model.constraints["flow_gate_upper"].dual
                results["details"]["gate_shadow_price"] = float(
                    gate_dual.values.item() if hasattr(gate_dual, "values") else gate_dual
                )
            except Exception:
                results["details"]["gate_shadow_price"] = "not extracted"

        # 5. Document the API mechanism
        results["details"]["api_mechanism"] = (
            "extra_functionality callback provides access to the linopy model. "
            "Custom constraints added via m.add_constraints() with xarray-aligned "
            "expressions referencing Line-s flow variables. No forking required."
        )
        results["details"]["documented_api"] = True
        results["details"]["requires_forking"] = False

        # Set pass status
        if gate_respected:
            results["status"] = "pass"

        results["workarounds"].append(
            "Manually assigned marginal_cost from MATPOWER gencost data — "
            "PyPSA pypower importer skips gencost on import (same as A-3)."
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
