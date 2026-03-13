"""
Test B-1: Custom Constraints — Flow Gate (custom_constraints)

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Achievable through documented API. No source patching. Dual value of
  custom constraint extractable and correct (≠0 when binding, =0 when non-binding).
  Objective increases when constraint is binding.
Tool: PyPSA 1.1.2
"""

import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")

# Solver configuration (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,
}


def load_network_a3_setup(network_file: str):
    """Load case39.m with same setup as A-3: differentiated costs + 70% branch derating."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)

    # Assign differentiated marginal costs (same as A-3)
    gen_names = sorted(n.generators.index)
    n_gens = len(gen_names)
    costs = np.linspace(10, 100, n_gens)
    for gen_name, cost in zip(gen_names, costs):
        n.generators.at[gen_name, "marginal_cost"] = float(cost)

    # Derate ALL branch flow limits by 70% (same as A-3)
    n.lines.s_nom = n.lines.s_nom * 0.7
    if len(n.transformers) > 0:
        n.transformers.s_nom = n.transformers.s_nom * 0.7

    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute flow gate custom constraint test — non-binding and binding cases.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # ----------------------------------------------------------------
        # Step 1: Non-binding case — threshold=10000 MW (unreachable)
        # ----------------------------------------------------------------
        n_nb = load_network_a3_setup(network_file)

        # First, probe linopy model variable dimension names
        # We need to call optimize once (or create_model) to inspect dims
        # Use extra_functionality to capture the variable name
        dim_probe = {}

        def probe_dims(n, snapshots):
            """Capture variable dimension names for Line-p."""
            if "Line-p" in n.model.variables:
                dim_probe["Line-p_dims"] = dict(n.model.variables["Line-p"].dims)
            # Enumerate all variable names to identify line flow variable
            dim_probe["all_variable_names"] = list(n.model.variables)

        # Run non-binding solve with probe
        gate_lines = ["L1", "L2"]  # PyPSA names lines L0, L1, L2... from case39.m
        nb_threshold = 10000.0  # MW — unreachable

        def make_flow_gate(threshold, gate_lines_list):
            def add_flow_gate(n, snapshots):
                # In PyPSA v1.1.2 the line apparent power variable is "Line-s"
                # (not "Line-p" as in earlier versions). Check both names for robustness.
                var_name = None
                for candidate in ["Line-s", "Line-p"]:
                    if candidate in n.model.variables:
                        var_name = candidate
                        break
                if var_name is None:
                    raise ValueError(
                        "Neither 'Line-s' nor 'Line-p' found in model. Available: "
                        + str(list(n.model.variables))
                    )

                var = n.model.variables[var_name]
                # Determine the dimension name for line assets (not "snapshot")
                line_dim = [d for d in var.dims if d != "snapshot"]
                if not line_dim:
                    raise ValueError(f"Cannot find line dimension in {var_name} dims: {var.dims}")
                line_dim_name = line_dim[0]

                # Filter to gate lines that exist in the network
                available_lines = var.coords[line_dim_name].values.tolist()
                valid_gate = [ln for ln in gate_lines_list if ln in available_lines]
                if not valid_gate:
                    raise ValueError(
                        f"None of gate lines {gate_lines_list} found in {available_lines[:10]}..."
                    )

                lhs = var.sel({line_dim_name: valid_gate}).sum(line_dim_name)
                n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")
                n._gate_lines_used = valid_gate
                n._gate_line_dim = line_dim_name
                n._line_var_name = var_name

            return add_flow_gate

        # Solve non-binding case
        status_nb, cond_nb = n_nb.optimize(
            extra_functionality=make_flow_gate(nb_threshold, gate_lines),
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        obj_nb = float(n_nb.objective)

        results["details"]["non_binding"] = {
            "threshold_mw": nb_threshold,
            "solver_status": str(status_nb),
            "solver_condition": str(cond_nb),
            "objective": obj_nb,
        }

        # Check dual of FlowGate constraint (non-binding)
        dual_nb = None
        if "FlowGate" in n_nb.model.constraints:
            dual_da = n_nb.model.constraints["FlowGate"].dual
            dual_nb = float(dual_da.values.flatten()[0]) if dual_da is not None else None
        results["details"]["non_binding"]["dual_flowgate"] = dual_nb

        # Inspect actual line flows to compute binding threshold
        p0_nb = n_nb.lines_t.p0
        gate_lines_used = getattr(n_nb, "_gate_lines_used", gate_lines)

        print(f"=== Non-binding case: objective={obj_nb:.2f}, FlowGate dual={dual_nb} ===")
        print(f"Gate lines used: {gate_lines_used}")
        if len(p0_nb) > 0 and gate_lines_used:
            flow_sum_nb = 0.0
            for gl in gate_lines_used:
                if gl in p0_nb.columns:
                    flow_sum_nb += float(p0_nb.iloc[0][gl])
            print(f"Unconstrained sum of flows on gate lines: {flow_sum_nb:.2f} MW")
            results["details"]["non_binding"]["unconstrained_flow_sum_mw"] = flow_sum_nb
            # Binding threshold = 75% of unconstrained sum — tight enough to bind,
            # but not so tight that the problem becomes infeasible.
            # Individual line capacity limits still apply; if even 75% is infeasible,
            # we'll detect it and fall back further.
            binding_threshold = max(abs(flow_sum_nb) * 0.75, 10.0)
        else:
            binding_threshold = 50.0  # Fallback if flow not available

        results["details"]["binding_threshold_mw"] = binding_threshold

        # ----------------------------------------------------------------
        # Step 2: Binding case — threshold = 75% of unconstrained flow sum
        # Retry with 90% if 75% is infeasible (gate may be too tight)
        # ----------------------------------------------------------------
        tried_thresholds = []
        for threshold_fraction in [0.75, 0.90, 0.95]:
            actual_binding_threshold = (
                flow_sum_nb * threshold_fraction if flow_sum_nb > 0 else binding_threshold
            )
            tried_thresholds.append(actual_binding_threshold)
            n_b = load_network_a3_setup(network_file)
            status_b, cond_b = n_b.optimize(
                extra_functionality=make_flow_gate(actual_binding_threshold, gate_lines),
                solver_name=SOLVER_NAME,
                solver_options=SOLVER_OPTIONS,
            )
            if str(status_b).lower() in ("ok", "optimal"):
                binding_threshold = actual_binding_threshold
                break

        obj_b = float(n_b.objective) if n_b.objective is not None else None
        results["details"]["binding_thresholds_tried"] = tried_thresholds

        results["details"]["binding"] = {
            "threshold_mw": binding_threshold,
            "solver_status": str(status_b),
            "solver_condition": str(cond_b),
            "objective": obj_b,
        }

        # Extract dual for binding case
        dual_b = None
        if "FlowGate" in n_b.model.constraints:
            dual_da_b = n_b.model.constraints["FlowGate"].dual
            dual_b = float(dual_da_b.values.flatten()[0]) if dual_da_b is not None else None
        results["details"]["binding"]["dual_flowgate"] = dual_b

        gate_lines_used_b = getattr(n_b, "_gate_lines_used", gate_lines)
        p0_b = n_b.lines_t.p0
        if len(p0_b) > 0 and gate_lines_used_b:
            flow_sum_b = sum(
                float(p0_b.iloc[0][gl]) for gl in gate_lines_used_b if gl in p0_b.columns
            )
            results["details"]["binding"]["actual_flow_sum_mw"] = flow_sum_b
        else:
            flow_sum_b = None

        print(f"=== Binding case: objective={obj_b}, FlowGate dual={dual_b} ===")
        print(f"Binding threshold: {binding_threshold:.2f} MW")
        if flow_sum_b is not None:
            print(f"Actual flow sum through gate: {flow_sum_b:.2f} MW")

        # ----------------------------------------------------------------
        # Step 3: Pass condition checks
        # ----------------------------------------------------------------
        errors = []

        # Check solver status
        if str(status_nb).lower() not in ("ok", "optimal"):
            errors.append(f"Non-binding solve failed: {status_nb}, {cond_nb}")
        if str(status_b).lower() not in ("ok", "optimal"):
            errors.append(f"Binding solve failed: {status_b}, {cond_b}")

        # Non-binding: dual should be ~0
        if dual_nb is None:
            errors.append("Could not extract dual from FlowGate constraint (non-binding case)")
        elif abs(dual_nb) > 1e-4:
            errors.append(f"Non-binding case: FlowGate dual={dual_nb:.6f} should be ~0")

        # Binding: dual should be nonzero
        if dual_b is None:
            errors.append("Could not extract dual from FlowGate constraint (binding case)")
        elif abs(dual_b) < 1e-6:
            errors.append(
                f"Binding case: FlowGate dual={dual_b:.6f} should be nonzero (constraint not actually binding?)"
            )

        # Objective should increase in binding case
        obj_increases = obj_b is not None and obj_b >= obj_nb * (1 - 1e-6)
        if not obj_increases:
            errors.append(
                f"Binding case objective ({obj_b}) should be >= non-binding ({obj_nb:.2f})"
            )

        results["errors"].extend(errors)

        results["details"]["pass_checks"] = {
            "dual_extractable_non_binding": dual_nb is not None,
            "dual_extractable_binding": dual_b is not None,
            "dual_is_zero_non_binding": dual_nb is not None and abs(dual_nb) < 1e-4,
            "dual_is_nonzero_binding": dual_b is not None and abs(dual_b) > 1e-6,
            "objective_increases_when_binding": obj_increases,
            "obj_nb": obj_nb,
            "obj_b": obj_b,
            "dual_nb": dual_nb,
            "dual_b": dual_b,
        }

        results["workarounds"].append(
            "extra_functionality callback passes n.model (linopy) for constraint injection — "
            "this is the documented public API for custom constraints in PyPSA v1.1.2"
        )

        if not errors:
            results["status"] = "pass"
        else:
            results["status"] = "fail"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
