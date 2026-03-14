"""
Test B-1: Add flow gate limit to DC OPF, read dual value of custom constraint.

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Achievable through a documented API or extension mechanism. No source
    patching or forking required. Dual value of custom constraint extractable and correctly
    reflects binding status.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS

Approach: GridCal has no public API for custom constraint injection into OPF. However,
the internal formulation uses PuLP as the LP modeling framework, and the `run_linear_opf_ts`
function returns the `LpModel` wrapper after solving. By monkey-patching the
`PulpLpModel.solve` method, we can intercept the model BEFORE it is solved, extract branch
flow expressions from existing constraints, construct a flowgate constraint, inject it,
and then let the solve proceed. Dual values are accessible via PuLP's `constraint.pi`.

This is a FRAGILE workaround: it depends on internal constraint naming conventions
(`br_flow_upper_lim_0_<branch_idx>`) and the internal PulpLpModel class.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal

# Cost mapping from gen_temporal_params.csv tech_class_key
COST_MAP = {
    "hydro": {"c1": 5.0, "c2": 0.005},
    "nuclear": {"c1": 10.0, "c2": 0.010},
    "coal_large": {"c1": 25.0, "c2": 0.025},
    "gas_CC": {"c1": 40.0, "c2": 0.040},
}

BRANCH_DERATING = 0.70

# Flowgate definition: FG_01 from flowgate_metadata.json
# Branches at indices 2 (bus 2->3) and 4 (bus 2->30), weights 1.0 each
FLOWGATE_BRANCH_INDICES = [2, 4]
FLOWGATE_WEIGHTS = [1.0, 1.0]
FLOWGATE_LIMIT_MW_BINDING = 400.0  # Tight limit that forces re-dispatch
FLOWGATE_LIMIT_MW_NONBINDING = 900.0  # Loose limit that doesn't bind


def _setup_grid(network_file: str, timeseries_dir: str | None):
    """Load grid, apply differentiated costs and branch derating."""

    grid = load_gridcal(network_file)
    generators = grid.get_generators()
    branches = grid.get_branches()

    # Apply differentiated costs
    ts_dir = Path(timeseries_dir) if timeseries_dir else None
    if ts_dir and (ts_dir / "gen_temporal_params.csv").exists():
        gen_params = {}
        with open(ts_dir / "gen_temporal_params.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                gen_params[int(row["gen_index"])] = row
        for idx, gen in enumerate(generators):
            if idx in gen_params:
                tech_key = gen_params[idx]["tech_class_key"]
                if tech_key in COST_MAP:
                    gen.Cost = COST_MAP[tech_key]["c1"]
                    gen.Cost2 = COST_MAP[tech_key]["c2"]
                    gen.Cost0 = 0.0

    # Apply 70% branch derating
    for branch in branches:
        if hasattr(branch, "rate") and branch.rate > 0:
            branch.rate = branch.rate * BRANCH_DERATING

    return grid


def _solve_with_flowgate(
    grid, fg_limit_mw: float, fg_branch_indices: list, fg_weights: list, fg_name: str
):
    """Solve DC OPF with a flowgate constraint injected via monkey-patch.

    Returns (opf_vars, model, fg_dual, fg_slack, fg_flow_total).
    """
    import pulp
    from VeraGridEngine.enumerations import MIPSolvers
    from VeraGridEngine.Simulations.OPF.Formulations.linear_opf_ts import run_linear_opf_ts
    from VeraGridEngine.Utils.MIP.pulp_interface import PulpLpModel

    Sbase = grid.Sbase
    original_solve = PulpLpModel.solve
    injection_info = {"done": False}

    def patched_solve(self, robust=False, show_logs=False, progress_text=None):
        if not injection_info["done"]:
            injection_info["done"] = True

            # Build flowgate expression from existing branch constraints
            fg_expr = pulp.LpAffineExpression()
            for br_idx, weight in zip(fg_branch_indices, fg_weights):
                cst_name = f"br_flow_upper_lim_0_{br_idx}"
                cst = self.model.constraints.get(cst_name)
                if cst is None:
                    raise RuntimeError(f"Branch constraint {cst_name} not found")

                # Extract flow expression (exclude slack vars)
                sp_name = f"flow_slack_pos_0_{br_idx}"
                sn_name = f"flow_slack_neg_0_{br_idx}"
                for var, coeff in cst.items():
                    if var.name != sp_name and var.name != sn_name:
                        fg_expr += var * coeff * weight

            # Add flowgate constraint
            fg_limit_pu = fg_limit_mw / Sbase
            self.model.addConstraint(fg_expr <= fg_limit_pu, fg_name)

        return original_solve(self, robust=robust, show_logs=show_logs, progress_text=progress_text)

    try:
        PulpLpModel.solve = patched_solve
        opf_vars, model = run_linear_opf_ts(
            grid=grid, time_indices=None, solver_type=MIPSolvers.HIGHS
        )
    finally:
        PulpLpModel.solve = original_solve

    # Extract dual value
    fg_cst = model.model.constraints.get(fg_name)
    fg_dual = fg_cst.pi if fg_cst else None
    fg_slack = fg_cst.slack if fg_cst else None

    # Compute actual flowgate flow
    flows = opf_vars.branch_vars.flows[0, :].astype(float)
    fg_flow_total = sum(flows[i] * w for i, w in zip(fg_branch_indices, fg_weights))

    return opf_vars, model, fg_dual, fg_slack, fg_flow_total


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute B-1 custom constraints test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        from VeraGridEngine.enumerations import MIPSolvers
        from VeraGridEngine.Simulations.OPF.Formulations.linear_opf_ts import run_linear_opf_ts

        # --- Step 1: Solve base case without flowgate ---
        grid_base = _setup_grid(network_file, timeseries_dir)
        opf_vars_base, model_base = run_linear_opf_ts(
            grid=grid_base, time_indices=None, solver_type=MIPSolvers.HIGHS
        )
        base_obj = model_base.fobj_value()
        base_flows = opf_vars_base.branch_vars.flows[0, :].astype(float)
        base_fg_flow = sum(
            base_flows[i] * w for i, w in zip(FLOWGATE_BRANCH_INDICES, FLOWGATE_WEIGHTS)
        )
        results["details"]["base_case"] = {
            "objective": float(base_obj),
            "flowgate_flow_mw": float(base_fg_flow),
            "converged": bool(opf_vars_base.acceptable_solution),
        }

        # --- Step 2: Solve with BINDING flowgate ---
        grid_bind = _setup_grid(network_file, timeseries_dir)
        opf_bind, model_bind, dual_bind, slack_bind, fg_flow_bind = _solve_with_flowgate(
            grid_bind,
            FLOWGATE_LIMIT_MW_BINDING,
            FLOWGATE_BRANCH_INDICES,
            FLOWGATE_WEIGHTS,
            "flowgate_FG01_binding",
        )

        binding_is_binding = abs(fg_flow_bind - FLOWGATE_LIMIT_MW_BINDING) < 0.5
        obj_bind = model_bind.fobj_value()

        results["details"]["binding_case"] = {
            "flowgate_limit_mw": FLOWGATE_LIMIT_MW_BINDING,
            "flowgate_flow_mw": float(fg_flow_bind),
            "is_binding": binding_is_binding,
            "objective": float(obj_bind),
            "cost_increase": float(obj_bind - base_obj),
            "dual_value": float(dual_bind) if dual_bind is not None else None,
            "slack": float(slack_bind) if slack_bind is not None else None,
            "converged": bool(opf_bind.acceptable_solution),
        }

        # --- Step 3: Solve with NON-BINDING flowgate ---
        grid_nb = _setup_grid(network_file, timeseries_dir)
        opf_nb, model_nb, dual_nb, slack_nb, fg_flow_nb = _solve_with_flowgate(
            grid_nb,
            FLOWGATE_LIMIT_MW_NONBINDING,
            FLOWGATE_BRANCH_INDICES,
            FLOWGATE_WEIGHTS,
            "flowgate_FG01_nonbinding",
        )

        nb_is_not_binding = fg_flow_nb < FLOWGATE_LIMIT_MW_NONBINDING - 0.5
        obj_nb = model_nb.fobj_value()

        results["details"]["nonbinding_case"] = {
            "flowgate_limit_mw": FLOWGATE_LIMIT_MW_NONBINDING,
            "flowgate_flow_mw": float(fg_flow_nb),
            "is_nonbinding": nb_is_not_binding,
            "objective": float(obj_nb),
            "dual_value": float(dual_nb) if dual_nb is not None else None,
            "slack": float(slack_nb) if slack_nb is not None else None,
            "converged": bool(opf_nb.acceptable_solution),
        }

        # --- Step 4: Validate results ---
        pass_checks = {
            "base_converged": bool(opf_vars_base.acceptable_solution),
            "binding_converged": bool(opf_bind.acceptable_solution),
            "nonbinding_converged": bool(opf_nb.acceptable_solution),
            "binding_constraint_enforced": binding_is_binding,
            "nonbinding_constraint_slack": nb_is_not_binding,
            "binding_dual_nonzero": dual_bind is not None and abs(dual_bind) > 1e-6,
            "nonbinding_dual_zero": dual_nb is not None and abs(dual_nb) < 1e-6,
            "binding_costs_more": obj_bind > base_obj + 1e-6,
        }
        results["details"]["pass_checks"] = pass_checks

        results["workarounds"].append(
            "Monkey-patched PulpLpModel.solve to inject flowgate constraint "
            "before LP solve. Extracted branch flow expressions from internal "
            "constraint naming convention (br_flow_upper_lim_0_<idx>). "
            "Dual values accessed via PuLP's constraint.pi attribute. "
            "Classification: FRAGILE — depends on internal constraint naming and "
            "PulpLpModel class structure."
        )

        if all(pass_checks.values()):
            results["status"] = "qualified_pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
