"""
Test B-1: Add a flow gate limit to DC OPF, read and assert on custom constraint
dual value, produce binding constraint report

Dimension: extensibility
Network: TINY (case39)
Pass condition: Achievable through a documented API or extension mechanism. No source
    patching or forking required. Dual value of custom constraint extractable and
    correctly reflects binding status.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")

# HiGHS solver settings per solver-config.md
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

# Flow gate definition: sum of flows on lines L15, L16, L17
# These form a corridor with significant positive flows in the base case.
FLOW_GATE_LINES = ["L15", "L16", "L17"]


def _load_network_with_costs(case_path: str):
    """Load MATPOWER .m file and set differentiated marginal costs.

    case39 has identical gencost (c1=0.3 for all generators), which creates
    LP degeneracy. We perturb costs slightly so the LP has a unique optimal
    dispatch, ensuring the flow gate constraint is binding when set below the
    unconstrained flow.
    """
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)

    gencost = cf.gencost.values
    workarounds = []
    num_gens = len(net.generators)
    costs_set = 0

    # Set differentiated marginal costs: base c1 + small perturbation per gen
    # This breaks degeneracy while keeping realistic cost ordering
    rng = np.random.default_rng(seed=42)
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])
            if cost_type == 2 and n_coeffs >= 2:
                c1 = float(cost_row[4 + n_coeffs - 2])
                # Add perturbation of +/- 10% to break degeneracy
                perturbation = rng.uniform(-0.1, 0.1) * c1
                net.generators.loc[gen_idx, "marginal_cost"] = c1 + perturbation
                costs_set += 1

    if costs_set > 0:
        workarounds.append(
            f"Manually set marginal_cost on {costs_set}/{num_gens} generators "
            "from gencost data with small perturbations to break LP degeneracy "
            "(PPC importer does not import gencost; case39 has identical c1=0.3 "
            "for all generators)"
        )

    return net, workarounds


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute the test and return structured results.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    try:
        # 1. Load network with costs (not timed)
        n, load_workarounds = _load_network_with_costs(network_file)
        results["workarounds"].extend(load_workarounds)

        # 2. Run baseline DCOPF (unconstrained) to determine flow gate level
        n.optimize(
            solver_name=SOLVER_NAME,
            solver_options={**SOLVER_OPTIONS, "output_flag": False},
        )
        baseline_objective = float(n.objective)
        baseline_flows = n.lines_t.p0.iloc[0].copy()
        baseline_gate_flow = sum(float(baseline_flows[line]) for line in FLOW_GATE_LINES)

        # Set limit to 80% of unconstrained flow to guarantee binding
        flow_gate_limit = baseline_gate_flow * 0.80

        # Record generator costs for reproducibility
        gen_costs = {
            gen: float(n.generators.loc[gen, "marginal_cost"]) for gen in n.generators.index
        }

        # 3. Re-load network for constrained run (optimize modifies state)
        n, _ = _load_network_with_costs(network_file)

        # 4. Use create_model / solve_model split to add custom constraint
        # This is the documented PyPSA extension mechanism for custom constraints.
        # API: n.optimize.create_model() builds the Linopy model at n.model,
        # then m.add_constraints() adds user constraints before solve_model().
        n.optimize.create_model()
        m = n.model

        # Access line flow variables from the Linopy model
        line_s = m["Line-s"]

        # Define flow gate: sum of signed flows on gate lines <= limit
        gate_expr = sum(line_s.sel(name=line) for line in FLOW_GATE_LINES)
        m.add_constraints(gate_expr <= flow_gate_limit, name="flow_gate")

        # Lines of code for the custom constraint addition:
        #   1: gate_expr = sum(line_s.sel(name=line) for line in FLOW_GATE_LINES)
        #   2: m.add_constraints(gate_expr <= flow_gate_limit, name="flow_gate")
        loc_custom_constraint = 2

        # 5. Solve with assign_all_duals=True to get custom constraint dual
        start = time.perf_counter()
        constrained_status = n.optimize.solve_model(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
            assign_all_duals=True,
        )
        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed

        converged = "ok" in str(constrained_status).lower()
        constrained_objective = float(n.objective)

        # 6. Extract constrained flows
        constrained_flows = n.lines_t.p0.iloc[0].copy()
        constrained_gate_flow = sum(float(constrained_flows[line]) for line in FLOW_GATE_LINES)

        # 7. Extract dual value of custom constraint
        flow_gate_dual = float(m.dual["flow_gate"].values.item())

        # Binding if dual is non-zero (within tolerance)
        is_binding = abs(flow_gate_dual) > 1e-6

        # 8. Constraint report
        constraint_report = {
            "constraint_name": "flow_gate",
            "definition": f"sum(flows on {FLOW_GATE_LINES}) <= {flow_gate_limit:.2f} MW",
            "unconstrained_gate_flow_MW": float(baseline_gate_flow),
            "constrained_gate_flow_MW": float(constrained_gate_flow),
            "flow_gate_limit_MW": flow_gate_limit,
            "dual_value": flow_gate_dual,
            "is_binding": is_binding,
            "objective_increase": constrained_objective - baseline_objective,
            "objective_increase_pct": (
                (constrained_objective - baseline_objective) / baseline_objective * 100
                if baseline_objective != 0
                else None
            ),
        }

        # 9. Pass condition: constraint achievable via documented API,
        #    dual extractable and reflects binding status
        gate_flow_within_limit = constrained_gate_flow <= flow_gate_limit + 1e-6
        constraint_forced_redispatch = constrained_objective >= baseline_objective - 1e-6
        dual_reflects_binding = is_binding

        pass_condition_met = (
            converged
            and gate_flow_within_limit
            and dual_reflects_binding
            and constraint_forced_redispatch
        )

        if pass_condition_met:
            results["status"] = "pass"

        results["details"] = {
            "converged": converged,
            "solver_status": str(constrained_status),
            "solver": SOLVER_NAME,
            "baseline_objective": baseline_objective,
            "constrained_objective": constrained_objective,
            "constraint_report": constraint_report,
            "loc_custom_constraint": loc_custom_constraint,
            "api_mechanism": "create_model() + m.add_constraints() + solve_model()",
            "dual_extraction": "m.dual['flow_gate'] via Linopy model",
            "assign_all_duals_needed": True,
            "generator_costs": gen_costs,
            "per_line_flows": {
                line: {
                    "unconstrained_MW": float(baseline_flows[line]),
                    "constrained_MW": float(constrained_flows[line]),
                }
                for line in FLOW_GATE_LINES
            },
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
