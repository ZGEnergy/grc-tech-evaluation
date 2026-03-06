"""B-1 (custom_constraints) -- Flow gate limit in DC OPF on ACTIVSg10k (MEDIUM).

Uses two-phase create_model() workflow. Constrains each gate line individually.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg10k.m")


def load_network_with_costs(filepath):
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
    if hasattr(cf, "gencost") and cf.gencost is not None:
        gc = cf.gencost.values
        for i, gen_name in enumerate(n.generators.index):
            if i < len(gc):
                cost_type = int(gc[i, 0])
                if cost_type == 2:
                    n_coeffs = int(gc[i, 3])
                    if n_coeffs == 2:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 4]
                    elif n_coeffs >= 3:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 5]
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.x == 0, "x"] = 1e-4
    return n


def run():
    errors = []
    workarounds = []
    details = {}
    try:
        # Base DC OPF
        n_base = load_network_with_costs(CASE_FILE)
        n_base.optimize(
            solver_name="highs", solver_options={"time_limit": 300, "presolve": "on", "threads": 1}
        )
        base_objective = float(n_base.objective)
        details["base_objective"] = round(base_objective, 4)

        # Find a highly loaded line to constrain
        base_flows = n_base.lines_t.p0.iloc[0]
        base_loading = (
            (base_flows.abs() / n_base.lines.s_nom).replace([np.inf, -np.inf], 0).fillna(0)
        )
        top_loaded = base_loading.nlargest(10)
        # Pick a binding or near-binding line
        gate_line = top_loaded.index[0]
        gate_base_flow = abs(float(base_flows[gate_line]))
        gate_s_nom = float(n_base.lines.loc[gate_line, "s_nom"])
        # Set threshold to 50% of current flow to force re-dispatch
        gate_threshold = round(gate_base_flow * 0.5, 1)
        details["gate_line"] = gate_line
        details["gate_base_flow_mw"] = round(gate_base_flow, 2)
        details["gate_s_nom"] = round(gate_s_nom, 2)
        details["gate_threshold_mw"] = gate_threshold

        # Constrained DC OPF
        n = load_network_with_costs(CASE_FILE)
        t0 = time.perf_counter()
        n.optimize.create_model()

        line_s = n.model.variables["Line-s"]
        gate_flow = line_s.sel(name=gate_line)
        n.model.add_constraints(gate_flow <= gate_threshold, name="flow_gate_upper")
        n.model.add_constraints(gate_flow >= -gate_threshold, name="flow_gate_lower")

        n.model.solve(solver_name="highs")
        n.optimize.assign_solution()
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["solver_status"] = str(n.model.status)
        details["constrained_objective"] = round(float(n.objective), 4)
        constrained_flow = abs(float(n.lines_t.p0.iloc[0][gate_line]))
        details["gate_flow_constrained_mw"] = round(constrained_flow, 4)
        details["gate_constraint_respected"] = constrained_flow <= gate_threshold + 0.1
        details["objective_increase"] = round(float(n.objective) - base_objective, 4)
        details["api_method"] = (
            "create_model() -> model.variables['Line-s'].sel(name=X) -> add_constraints() -> solve() -> assign_solution()"
        )
        details["loc_custom_constraint"] = 4

        workarounds.append(
            {
                "type": "stable",
                "description": "Fix zero-impedance transformers (x=1e-4) to avoid SVD failure in post_processing.",
            }
        )

        assert details["gate_constraint_respected"], (
            f"Flow gate violated: {constrained_flow} > {gate_threshold}"
        )
        assert details["objective_increase"] >= 0, "Constraint should not decrease cost"
        status = "PASS"
    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
    return {
        "test_id": "B-1",
        "slug": "custom_constraints",
        "tier": "MEDIUM",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
