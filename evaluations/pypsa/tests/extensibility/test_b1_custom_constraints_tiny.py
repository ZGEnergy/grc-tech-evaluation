"""B-1 (custom_constraints) — Add flow gate limit to DC OPF on IEEE 39-bus (TINY).

Pass condition: Achievable through documented API, no source patching.
Uses create_model() / add_constraints() / solve_model() two-phase workflow.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case39.m")


def load_network_with_costs(filepath: str | Path) -> pypsa.Network:
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    if hasattr(cf, "gencost") and cf.gencost is not None:
        ppc["gencost"] = cf.gencost.values
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)

    gc = cf.gencost
    for i, gen_name in enumerate(n.generators.index):
        row = gc.iloc[i]
        n_cost = int(row["NCOST"])
        if n_cost == 3:
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]
            n.generators.loc[gen_name, "marginal_cost_quadratic"] = row["C2"]
        elif n_cost == 2:
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]

    return n


def run() -> dict:
    """Execute B-1 custom constraints test."""
    errors = []
    workarounds = []
    details = {}

    try:
        # Step 1: Solve base DC OPF (without flow gate) for comparison
        n_base = load_network_with_costs(CASE_FILE)
        n_base.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        base_objective = float(n_base.objective)
        details["base_objective"] = round(base_objective, 4)

        # Step 2: Solve with custom flow gate constraint
        n = load_network_with_costs(CASE_FILE)

        t0 = time.perf_counter()

        # Two-phase approach: create_model, add constraint, solve_model
        n.optimize.create_model()

        # Define flow gate: sum of flows on lines L0, L1, L2 <= 200 MW
        gate_lines = ["L0", "L1", "L2"]
        gate_threshold = 200.0  # MW

        # Access Line-s variable (dims: snapshot, name)
        line_s = n.model.variables["Line-s"]
        gate_flows = line_s.sel(name=gate_lines)

        # Constraint: sum of flows <= threshold (both directions)
        gate_sum = gate_flows.sum("name")
        n.model.add_constraints(gate_sum <= gate_threshold, name="flow_gate_upper")
        n.model.add_constraints(-gate_sum <= gate_threshold, name="flow_gate_lower")

        # Solve and assign solution back to network
        n.model.solve(solver_name="highs")
        n.optimize.assign_solution()
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["solver_status"] = str(n.model.status)
        details["constrained_objective"] = round(float(n.objective), 4)
        details["gate_lines"] = gate_lines
        details["gate_threshold_mw"] = gate_threshold

        # Check constrained flows
        constrained_flows = n.lines_t.p0.iloc[0]
        gate_flow_total = sum(constrained_flows[ln] for ln in gate_lines)
        details["gate_flow_total_mw"] = round(float(gate_flow_total), 4)
        details["gate_constraint_respected"] = abs(gate_flow_total) <= gate_threshold + 1e-3

        # Compare base vs constrained
        details["objective_increase"] = round(float(n.objective) - base_objective, 4)

        details["dispatch"] = {
            k: round(v, 2) for k, v in n.generators_t.p.iloc[0].to_dict().items()
        }

        # LMPs — may not be assigned when using manual model.solve() path
        lmps = n.buses_t.marginal_price
        if lmps.size > 0:
            details["lmp_range"] = [
                round(float(lmps.values.min()), 4),
                round(float(lmps.values.max()), 4),
            ]
        else:
            details["lmp_note"] = (
                "LMPs not auto-assigned via manual model.solve() + assign_solution(). "
                "Shadow prices available via n.model.constraints duals."
            )

        details["api_method"] = (
            "create_model() -> model.variables['Line-s'].sel(name=...).sum('name') "
            "-> model.add_constraints() -> model.solve() -> assign_solution()"
        )
        details["loc_custom_constraint"] = 6  # lines to add constraint

        assert details["gate_constraint_respected"], "Flow gate constraint violated"
        assert details["objective_increase"] > 0, "Constraint should increase cost"
        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "B-1",
        "slug": "custom_constraints",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
