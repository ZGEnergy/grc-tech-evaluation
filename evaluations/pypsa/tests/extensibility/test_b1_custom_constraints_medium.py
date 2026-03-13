"""
Test B-1: Custom Constraints — Flow Gate (custom_constraints)

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
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
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# Solver configuration (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,
}


def load_network(network_file: str):
    """Load ACTIVSg10k with differentiated costs. No branch derating — base network is feasible."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    n = pypsa.Network()
    # ACTIVSg10k has 2462 lines with zero s_nom (no explicit thermal rating).
    # Set those to a large unconstrained value (100 GVA) so OPF is feasible.
    # Do NOT derate — 70% derating makes the ACTIVSg10k OPF infeasible.
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=100000.0)

    # Assign differentiated marginal costs ($10–$100/MWh)
    gen_names = sorted(n.generators.index)
    n_gens = len(gen_names)
    costs = np.linspace(10, 100, n_gens)
    for gen_name, cost in zip(gen_names, costs):
        n.generators.at[gen_name, "marginal_cost"] = float(cost)

    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute flow gate custom constraint test on 10k-bus network.

    Approach:
    1. Run unconstrained OPF to find the actual maximum-flow line.
    2. Non-binding case: gate threshold = 2× max_flow (constraint cannot bind).
    3. Binding case: gate threshold = 0.5× max_flow on that single high-flow line
       (constraint binds, forcing rerouting).

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
        # Step 0: Pilot solve — unconstrained OPF to find high-flow lines
        # ----------------------------------------------------------------
        print("Loading 10k network for pilot (unconstrained) OPF...")
        n_pilot = load_network(network_file)

        n_lines = len(n_pilot.lines)
        n_buses = len(n_pilot.buses)
        results["details"]["n_buses"] = n_buses
        results["details"]["n_lines"] = n_lines
        results["details"]["n_generators"] = len(n_pilot.generators)

        print("Running unconstrained pilot OPF...")
        t_pilot_start = time.perf_counter()
        status_pilot, cond_pilot = n_pilot.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        t_pilot_elapsed = time.perf_counter() - t_pilot_start
        print(f"Pilot OPF: {status_pilot}, t={t_pilot_elapsed:.2f}s")

        if str(status_pilot).lower() not in ("ok", "optimal"):
            results["errors"].append(f"Pilot OPF failed: {status_pilot}, {cond_pilot}")
            return results

        obj_pilot = float(n_pilot.objective)
        results["details"]["pilot_objective"] = obj_pilot
        results["details"]["pilot_seconds"] = t_pilot_elapsed

        # Find the single highest-flow line in the unconstrained solution
        p0_pilot = n_pilot.lines_t.p0
        if len(p0_pilot) == 0 or len(p0_pilot.columns) == 0:
            results["errors"].append("No line flows in pilot OPF result")
            return results

        # Pick the highest-flow line with POSITIVE flow (so <= threshold binds correctly).
        # The line flow variable Line-s can be negative (reverse direction).
        # A one-sided <= constraint only binds for positive flows.
        pos_flows = p0_pilot.iloc[0]
        pos_flows_only = pos_flows[pos_flows > 0]
        if len(pos_flows_only) == 0:
            # Fallback: use absolute value and add two-sided constraint
            abs_flows = p0_pilot.iloc[0].abs()
            max_flow_line = abs_flows.idxmax()
            max_flow_mw = float(abs_flows[max_flow_line])
        else:
            max_flow_line = pos_flows_only.idxmax()
            max_flow_mw = float(pos_flows_only[max_flow_line])
        print(f"Highest positive-flow line: {max_flow_line}, flow={max_flow_mw:.2f} MW")

        results["details"]["pilot_max_flow_line"] = str(max_flow_line)
        results["details"]["pilot_max_flow_mw"] = max_flow_mw

        # Gate on the single highest-flow line
        gate_lines = [max_flow_line]
        print(f"Gate lines selected: {gate_lines}")

        def make_flow_gate(threshold, gate_lines_list):
            def add_flow_gate(n, snapshots):
                # In PyPSA v1.1.2 the line apparent power variable is "Line-s"
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
                line_dim = [d for d in var.dims if d != "snapshot"]
                if not line_dim:
                    raise ValueError(f"Cannot find line dimension in {var_name} dims: {var.dims}")
                line_dim_name = line_dim[0]

                available_lines = var.coords[line_dim_name].values.tolist()
                valid_gate = [ln for ln in gate_lines_list if ln in available_lines]
                if not valid_gate:
                    raise ValueError(f"None of gate lines {gate_lines_list} found in model")

                lhs = var.sel({line_dim_name: valid_gate}).sum(line_dim_name)
                # One-sided gate: sum(Line-s) <= threshold
                # Works correctly when gate lines have positive flow in unconstrained solution.
                n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")
                n._gate_lines_used = valid_gate
                n._line_var_name = var_name

            return add_flow_gate

        # ----------------------------------------------------------------
        # Step 1: Non-binding case — threshold = 2× max_flow (unreachable)
        # ----------------------------------------------------------------
        nb_threshold = max_flow_mw * 2.0
        print(f"Non-binding threshold: {nb_threshold:.2f} MW (2x max flow)")

        print("Loading 10k network for non-binding case...")
        n_nb = load_network(network_file)

        print("Solving non-binding OPF...")
        t_nb_start = time.perf_counter()
        status_nb, cond_nb = n_nb.optimize(
            extra_functionality=make_flow_gate(nb_threshold, gate_lines),
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
            assign_all_duals=True,
        )
        t_nb_elapsed = time.perf_counter() - t_nb_start
        obj_nb = float(n_nb.objective)
        print(f"Non-binding solve: {status_nb}, obj={obj_nb:.2f}, t={t_nb_elapsed:.2f}s")

        results["details"]["non_binding"] = {
            "threshold_mw": nb_threshold,
            "solver_status": str(status_nb),
            "solver_condition": str(cond_nb),
            "objective": obj_nb,
            "solve_seconds": t_nb_elapsed,
        }

        # Extract dual of FlowGate (non-binding)
        dual_nb = None
        if "FlowGate" in n_nb.model.constraints:
            dual_da = n_nb.model.constraints["FlowGate"].dual
            dual_nb = float(dual_da.values.flatten()[0]) if dual_da is not None else None
        results["details"]["non_binding"]["dual_flowgate"] = dual_nb
        print(f"Non-binding FlowGate dual: {dual_nb}")

        # Actual gate flow in non-binding case
        p0_nb = n_nb.lines_t.p0
        gate_lines_used = getattr(n_nb, "_gate_lines_used", gate_lines)
        flow_sum_nb = 0.0
        if len(p0_nb) > 0:
            for gl in gate_lines_used:
                if gl in p0_nb.columns:
                    flow_sum_nb += float(p0_nb.iloc[0][gl])
        print(f"Non-binding gate flow sum: {flow_sum_nb:.2f} MW")
        results["details"]["non_binding"]["unconstrained_flow_sum_mw"] = flow_sum_nb

        # ----------------------------------------------------------------
        # Step 2: Binding case — threshold = 0.5× max_flow from pilot
        # The pilot max_flow_line carries significant flow; halving it must
        # bind (the optimizer cannot trivially reroute).
        # ----------------------------------------------------------------
        tried_thresholds = []
        binding_threshold = None
        status_b = None
        cond_b = None
        n_b = None
        t_b_elapsed = None

        # Try fractions of the pilot max flow — stop at first feasible
        for frac in [0.50, 0.60, 0.70, 0.80, 0.90]:
            bt = max_flow_mw * frac
            tried_thresholds.append(bt)
            print(f"Trying binding threshold {bt:.2f} MW (fraction={frac} of max_flow)...")
            n_b = load_network(network_file)
            t_b_start = time.perf_counter()
            status_b, cond_b = n_b.optimize(
                extra_functionality=make_flow_gate(bt, gate_lines),
                solver_name=SOLVER_NAME,
                solver_options=SOLVER_OPTIONS,
                assign_all_duals=True,
            )
            t_b_elapsed = time.perf_counter() - t_b_start
            if str(status_b).lower() in ("ok", "optimal"):
                binding_threshold = bt
                print(f"Binding solve succeeded: {status_b}, t={t_b_elapsed:.2f}s")
                break
            else:
                print(f"Binding solve failed: {status_b} at threshold {bt:.2f}")

        results["details"]["binding_thresholds_tried"] = tried_thresholds

        obj_b = None
        dual_b = None
        flow_sum_b = None

        if n_b is not None and str(status_b).lower() in ("ok", "optimal"):
            obj_b = float(n_b.objective)
            if "FlowGate" in n_b.model.constraints:
                dual_da_b = n_b.model.constraints["FlowGate"].dual
                dual_b = float(dual_da_b.values.flatten()[0]) if dual_da_b is not None else None

            p0_b = n_b.lines_t.p0
            gate_lines_used_b = getattr(n_b, "_gate_lines_used", gate_lines)
            if len(p0_b) > 0:
                flow_sum_b = sum(
                    float(p0_b.iloc[0][gl]) for gl in gate_lines_used_b if gl in p0_b.columns
                )
            print(f"Binding case: obj={obj_b:.2f}, dual={dual_b}, gate_flow={flow_sum_b}")

        results["details"]["binding"] = {
            "threshold_mw": binding_threshold,
            "solver_status": str(status_b),
            "solver_condition": str(cond_b),
            "objective": obj_b,
            "dual_flowgate": dual_b,
            "actual_flow_sum_mw": flow_sum_b,
            "solve_seconds": t_b_elapsed,
        }

        # ----------------------------------------------------------------
        # Step 3: Pass condition checks
        # ----------------------------------------------------------------
        errors = []

        if str(status_nb).lower() not in ("ok", "optimal"):
            errors.append(f"Non-binding solve failed: {status_nb}, {cond_nb}")
        if binding_threshold is None or str(status_b).lower() not in ("ok", "optimal"):
            errors.append(f"Binding solve failed at all thresholds: last status={status_b}")

        if dual_nb is None:
            errors.append("Could not extract dual from FlowGate constraint (non-binding case)")
        elif abs(dual_nb) > 1e-4:
            errors.append(f"Non-binding case: FlowGate dual={dual_nb:.6f} should be ~0")

        if dual_b is None and binding_threshold is not None:
            errors.append("Could not extract dual from FlowGate constraint (binding case)")
        elif dual_b is not None and abs(dual_b) < 1e-6:
            errors.append(
                f"Binding case: FlowGate dual={dual_b:.6f} should be nonzero (constraint not binding?)"
            )

        obj_increases = obj_b is not None and obj_b >= obj_nb * (1 - 1e-6)
        if obj_b is not None and not obj_increases:
            errors.append(
                f"Binding case objective ({obj_b:.2f}) should be >= non-binding ({obj_nb:.2f})"
            )

        results["details"]["pass_checks"] = {
            "dual_extractable_non_binding": dual_nb is not None,
            "dual_extractable_binding": dual_b is not None,
            "dual_is_zero_non_binding": dual_nb is not None and abs(dual_nb) < 1e-4,
            "dual_is_nonzero_binding": dual_b is not None and abs(dual_b) > 1e-6,
            "objective_increases_when_binding": obj_increases,
        }

        results["workarounds"].append(
            "extra_functionality callback passes n.model (linopy) for constraint injection — "
            "this is the documented public API for custom constraints in PyPSA v1.1.2"
        )
        results["workarounds"].append(
            "Line flow variable is 'Line-s' (apparent power) in PyPSA v1.1.2, not 'Line-p'"
        )

        results["errors"].extend(errors)
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
