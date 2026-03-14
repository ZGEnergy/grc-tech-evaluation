"""
Test B-1: Add a flow gate limit to the DC OPF formulation from A-3

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Achievable through a documented API or extension mechanism. No source
  patching or forking required. Dual value of custom constraint extractable and
  correctly reflects binding status.
Tool: PyPSA 1.1.2
"""

import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
DEFAULT_TIMESERIES = str(REPO_ROOT / "data" / "timeseries" / "case39")

# Solver configuration (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,
}


def build_a3_network(network_file: str, timeseries_dir: str | None = None):
    """Build A-3 style DC OPF network: differentiated costs + 70% branch derating.

    Uses the shared matpower_loader for standardized loading, then applies
    Modified Tiny augmentation (differentiated costs from gen_temporal_params.csv)
    and 70% branch derating for congestion.
    """
    from matpower_loader import load_pypsa

    n = load_pypsa(network_file)

    # Apply differentiated costs from Modified Tiny data
    if timeseries_dir is not None:
        ts_dir = Path(timeseries_dir)
        gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

        # Cost mapping from README: tech_class_key -> c1 ($/MWh)
        cost_map = {
            "hydro": 5.0,
            "nuclear": 10.0,
            "coal_large": 25.0,
            "gas_CC": 40.0,
        }

        gen_class = pd.read_csv(ts_dir / "gen_classification.csv")
        gen_names = sorted(n.generators.index)

        for _, row in gen_class.iterrows():
            gen_idx = int(row["gen_index"])
            if gen_idx < len(gen_names):
                tech_key = gen_params.iloc[gen_idx]["tech_class_key"]
                cost = cost_map.get(tech_key, 30.0)
                n.generators.at[gen_names[gen_idx], "marginal_cost"] = cost
    else:
        # Fallback: simple differentiated costs via linspace
        gen_names = sorted(n.generators.index)
        costs = np.linspace(10, 100, len(gen_names))
        for gen_name, cost in zip(gen_names, costs):
            n.generators.at[gen_name, "marginal_cost"] = float(cost)

    # Derate ALL branch flow limits by 70% for congestion
    n.lines.s_nom = n.lines.s_nom * 0.7
    if len(n.transformers) > 0:
        n.transformers.s_nom = n.transformers.s_nom * 0.7

    return n


def find_gate_branches(n):
    """Identify branches for flowgate FG_01 (buses 2->3 and 2->30).

    Returns dict mapping component type ('Line' or 'Transformer') to list of names.
    """
    gate = {"Line": [], "Transformer": []}
    target_pairs = {("2", "3"), ("3", "2"), ("2", "30"), ("30", "2")}

    for ln in n.lines.index:
        pair = (str(n.lines.at[ln, "bus0"]), str(n.lines.at[ln, "bus1"]))
        if pair in target_pairs:
            gate["Line"].append(ln)

    for t in n.transformers.index:
        pair = (str(n.transformers.at[t, "bus0"]), str(n.transformers.at[t, "bus1"]))
        if pair in target_pairs:
            gate["Transformer"].append(t)

    return {k: v for k, v in gate.items() if v}


def make_flow_gate_callback(gate_branches: dict, threshold: float):
    """Create extra_functionality callback adding a flow gate constraint.

    gate_branches: dict mapping component type ('Line', 'Transformer') to list of names.
    threshold: MW limit for the sum of flows across all gate branches.

    Uses PyPSA's documented extra_functionality API: the callback receives
    (n, snapshots) and can access n.model (linopy Model) to add constraints.
    """

    def add_flow_gate(n, snapshots):
        flow_terms = []

        for comp_type, branch_names in gate_branches.items():
            # PyPSA v1.1.2 names the apparent power variable as "<CompType>-s"
            var_name = f"{comp_type}-s"
            if var_name not in n.model.variables:
                # Fallback to "-p" if "-s" not available
                var_name = f"{comp_type}-p"
            if var_name not in n.model.variables:
                raise ValueError(
                    f"Cannot find flow variable for {comp_type}. "
                    f"Available: {list(n.model.variables)}"
                )

            var = n.model.variables[var_name]
            # Find the branch dimension name (not "snapshot")
            branch_dim = [d for d in var.dims if d != "snapshot"]
            if not branch_dim:
                raise ValueError(f"No branch dim in {var_name}: dims={var.dims}")
            dim_name = branch_dim[0]

            available = var.coords[dim_name].values.tolist()
            valid = [b for b in branch_names if b in available]
            if valid:
                flow_terms.append(var.sel({dim_name: valid}).sum(dim_name))

        if not flow_terms:
            raise ValueError("No valid gate branches found in model variables")

        # Sum across all component types
        lhs = flow_terms[0]
        for term in flow_terms[1:]:
            lhs = lhs + term

        n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")

    return add_flow_gate


def extract_gate_flow(n, gate_branches: dict) -> float:
    """Sum actual power flows across gate branches after solve."""
    total = 0.0
    for comp_type, branch_names in gate_branches.items():
        if comp_type == "Line":
            p0 = n.lines_t.p0
        elif comp_type == "Transformer":
            p0 = n.transformers_t.p0
        else:
            continue
        if len(p0) > 0:
            for b in branch_names:
                if b in p0.columns:
                    total += float(p0.iloc[0][b])
    return total


def run(
    network_file: str = DEFAULT_NETWORK,
    timeseries_dir: str | None = DEFAULT_TIMESERIES,
) -> dict:
    """Execute flow gate custom constraint test -- non-binding AND binding cases.

    Guardrail per spec: includes both a non-binding case (verify dual=0) and a
    binding case (set constraint at ~50% of unconstrained flow, verify dual != 0
    and objective increases).
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
        # Identify gate branches (FG_01: 2->3 line + 2->30 transformer)
        n_probe = build_a3_network(network_file, timeseries_dir)
        gate_branches = find_gate_branches(n_probe)

        all_gate_names = []
        for comp, names in gate_branches.items():
            for name in names:
                all_gate_names.append(f"{comp}:{name}")
        results["details"]["gate_branches"] = all_gate_names

        if not gate_branches:
            results["errors"].append("Could not find flowgate branches (2->3, 2->30)")
            results["wall_clock_seconds"] = time.perf_counter() - start
            return results

        # ----------------------------------------------------------------
        # Step 1: Non-binding case -- threshold = 10000 MW (unreachable)
        # ----------------------------------------------------------------
        nb_threshold = 10000.0
        n_nb = build_a3_network(network_file, timeseries_dir)
        status_nb, cond_nb = n_nb.optimize(
            extra_functionality=make_flow_gate_callback(gate_branches, nb_threshold),
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        obj_nb = float(n_nb.objective)

        # Extract dual of FlowGate constraint (non-binding -> should be ~0)
        dual_nb = None
        if "FlowGate" in n_nb.model.constraints:
            dual_da = n_nb.model.constraints["FlowGate"].dual
            if dual_da is not None:
                dual_nb = float(dual_da.values.flatten()[0])

        flow_sum_nb = extract_gate_flow(n_nb, gate_branches)

        results["details"]["non_binding"] = {
            "threshold_mw": nb_threshold,
            "solver_status": str(status_nb),
            "solver_condition": str(cond_nb),
            "objective": obj_nb,
            "dual_flowgate": dual_nb,
            "unconstrained_flow_sum_mw": flow_sum_nb,
        }

        print(
            f"=== Non-binding: obj={obj_nb:.2f}, dual={dual_nb}, flow_sum={flow_sum_nb:.2f} MW ==="
        )

        # ----------------------------------------------------------------
        # Step 2: Binding case -- threshold = ~50% of unconstrained flow sum
        # Per spec: "set constraint at ~50% of unconstrained flow"
        # Try progressively looser fractions if too tight
        # ----------------------------------------------------------------
        binding_threshold = None
        n_b = None
        status_b = cond_b = None
        for fraction in [0.50, 0.60, 0.75, 0.90]:
            trial = abs(flow_sum_nb) * fraction if abs(flow_sum_nb) > 10 else 50.0
            n_trial = build_a3_network(network_file, timeseries_dir)
            s, c = n_trial.optimize(
                extra_functionality=make_flow_gate_callback(gate_branches, trial),
                solver_name=SOLVER_NAME,
                solver_options=SOLVER_OPTIONS,
            )
            if str(s).lower() in ("ok", "optimal"):
                binding_threshold = trial
                n_b = n_trial
                status_b = s
                cond_b = c
                print(f"  Binding at {fraction * 100:.0f}% ({trial:.1f} MW): feasible")
                break
            else:
                print(f"  Binding at {fraction * 100:.0f}% ({trial:.1f} MW): infeasible")

        if n_b is None:
            results["errors"].append(
                "All binding threshold fractions produced infeasible solutions"
            )
            results["wall_clock_seconds"] = time.perf_counter() - start
            return results

        obj_b = float(n_b.objective)

        # Extract dual (binding -> should be != 0)
        dual_b = None
        if "FlowGate" in n_b.model.constraints:
            dual_da_b = n_b.model.constraints["FlowGate"].dual
            if dual_da_b is not None:
                dual_b = float(dual_da_b.values.flatten()[0])

        flow_sum_b = extract_gate_flow(n_b, gate_branches)

        results["details"]["binding"] = {
            "threshold_mw": binding_threshold,
            "solver_status": str(status_b),
            "solver_condition": str(cond_b),
            "objective": obj_b,
            "dual_flowgate": dual_b,
            "actual_flow_sum_mw": flow_sum_b,
        }

        print(
            f"=== Binding: obj={obj_b:.2f}, dual={dual_b}, "
            f"threshold={binding_threshold:.2f}, actual_flow={flow_sum_b:.2f} MW ==="
        )

        # ----------------------------------------------------------------
        # Step 3: Pass condition checks
        # ----------------------------------------------------------------
        errors = []

        if str(status_nb).lower() not in ("ok", "optimal"):
            errors.append(f"Non-binding solve failed: {status_nb}, {cond_nb}")
        if str(status_b).lower() not in ("ok", "optimal"):
            errors.append(f"Binding solve failed: {status_b}, {cond_b}")

        # Non-binding: dual should be ~0
        if dual_nb is None:
            errors.append("Could not extract dual from FlowGate constraint (non-binding case)")
        elif abs(dual_nb) > 1e-4:
            errors.append(f"Non-binding dual={dual_nb:.6f} should be ~0")

        # Binding: dual should be nonzero
        if dual_b is None:
            errors.append("Could not extract dual from FlowGate constraint (binding case)")
        elif abs(dual_b) < 1e-6:
            errors.append(f"Binding dual={dual_b:.6f} should be nonzero")

        # Objective should increase when constraint binds
        obj_increases = obj_b is not None and obj_b >= obj_nb * (1 - 1e-6)
        if not obj_increases:
            errors.append(f"Binding objective ({obj_b}) should be >= non-binding ({obj_nb:.2f})")

        results["errors"].extend(errors)
        results["details"]["pass_checks"] = {
            "dual_extractable_non_binding": dual_nb is not None,
            "dual_extractable_binding": dual_b is not None,
            "dual_zero_non_binding": dual_nb is not None and abs(dual_nb) < 1e-4,
            "dual_nonzero_binding": dual_b is not None and abs(dual_b) > 1e-6,
            "objective_increases_when_binding": obj_increases,
        }

        if not errors:
            results["status"] = "pass"

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
