"""
Test B-1: Add flow gate limit to DC OPF and assert on dual value

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Achievable through a documented API or extension mechanism.
    No source patching or forking required. Dual value of custom constraint
    extractable and correctly reflects binding status.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

# Differentiated cost curves (same as A-3)
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}

BRANCH_DERATING = 0.70


def _setup_dcopf(net, timeseries_dir: str) -> None:
    """Set up the network for DC OPF (same pattern as A-3)."""
    import pandapower as pp

    ts_dir = Path(timeseries_dir)
    gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

    for idx in net.gen.index:
        net.gen.at[idx, "controllable"] = True
        net.gen.at[idx, "min_p_mw"] = 0.0
    for idx in net.ext_grid.index:
        net.ext_grid.at[idx, "controllable"] = True
        net.ext_grid.at[idx, "min_p_mw"] = -9999.0
        net.ext_grid.at[idx, "max_p_mw"] = 9999.0

    net.bus["min_vm_pu"] = 0.9
    net.bus["max_vm_pu"] = 1.1

    net.poly_cost.drop(net.poly_cost.index, inplace=True)
    if hasattr(net, "pwl_cost"):
        net.pwl_cost.drop(net.pwl_cost.index, inplace=True)

    for _, row in gen_params.iterrows():
        tech = row["tech_class_key"]
        costs = COST_BY_TECH.get(tech, COST_BY_TECH["gas_CC"])
        bus_id_pp = int(row["bus_id"]) - 1
        ext_match = net.ext_grid[net.ext_grid["bus"] == bus_id_pp]
        gen_match = net.gen[net.gen["bus"] == bus_id_pp]
        if len(ext_match) > 0:
            pp.create_poly_cost(
                net,
                element=ext_match.index[0],
                et="ext_grid",
                cp1_eur_per_mw=costs["cp1"],
                cp2_eur_per_mw2=costs["cp2"],
                cp0_eur=0.0,
            )
        elif len(gen_match) > 0:
            pp.create_poly_cost(
                net,
                element=gen_match.index[0],
                et="gen",
                cp1_eur_per_mw=costs["cp1"],
                cp2_eur_per_mw2=costs["cp2"],
                cp0_eur=0.0,
            )

    net.line["max_loading_percent"] = 100.0
    net.line["max_i_ka"] = net.line["max_i_ka"] * BRANCH_DERATING
    if len(net.trafo) > 0:
        net.trafo["max_loading_percent"] = 100.0


def _add_flowgate_constraint(om, args):
    """PYPOWER userfcn callback: add flow gate limit as a linear constraint.

    In the DC OPF, branch flow = Bf @ Va + Pfinj. The OPF variables are [Va, Pg].
    To constrain flow on a specific branch, we add:
        -limit <= Bf[branch_idx, :] @ Va + Pfinj[branch_idx] <= limit
    which in terms of the [Va, Pg] variable vector is:
        -limit - Pfinj <= [Bf_row, 0...0] @ [Va; Pg] <= limit - Pfinj
    """
    gate_branch_idx = args["gate_branch_idx"]
    gate_limit_pu = args["gate_limit_pu"]
    Bf = args["Bf"]
    Pfinj = args["Pfinj"]

    ppc = om.get_ppc()
    nb = ppc["bus"].shape[0]
    ng = ppc["gen"].shape[0]

    # Flow on gate branch = Bf[gate_branch_idx, :] @ Va + Pfinj[gate_branch_idx]
    # Constraint: -limit <= flow <= limit
    # => -limit - Pfinj <= Bf_row @ Va <= limit - Pfinj
    # In terms of [Va, Pg]: A = [Bf_row | zeros(1, ng)]

    Bf_row = Bf[gate_branch_idx, :].toarray().flatten()
    pfinj_val = float(Pfinj[gate_branch_idx])

    A_va = csr_matrix(Bf_row.reshape(1, nb))
    A_pg = csr_matrix((1, ng))
    A_gate = hstack([A_va, A_pg], format="csr")

    lb = np.array([-gate_limit_pu - pfinj_val])
    ub = np.array([gate_limit_pu - pfinj_val])

    om.add_constraints("flowgate", A_gate, lb, ub, ["Va", "Pg"])
    return om


def _run_dcopf_with_flowgate(net, gate_branch_idx, gate_limit_mw):
    """Run DC OPF with a custom flow gate constraint.

    Replaces pandapower's _optimal_powerflow with a version that injects
    a flow gate userfcn and captures the full PYPOWER result dict.

    Returns (converged, objective, flowgate_dual, captured_result).
    """
    import pandapower as pp
    import pandapower.optimal_powerflow as opf_mod
    import pandapower.run as run_mod
    from pandapower.auxiliary import OPFNotConverged, _add_auxiliary_elements, _clean_up
    from pandapower.pd2ppc import _pd2ppc
    from pandapower.pypower.add_userfcn import add_userfcn
    from pandapower.pypower.idx_bus import VM
    from pandapower.pypower.makeBdc import makeBdc
    from pandapower.pypower.opf import opf
    from pandapower.pypower.ppoption import ppoption
    from pandapower.results import (
        _copy_results_ppci_to_ppc,
        _extract_results,
        init_results,
        verify_results,
    )

    captured_result = {}

    def _custom_optimal_powerflow(net_inner, verbose, suppress_warnings, **kwargs):
        """Custom _optimal_powerflow that injects flow gate userfcn."""
        ac = net_inner["_options"]["ac"]
        init = net_inner["_options"]["init"]

        if "OPF_FLOW_LIM" not in kwargs:
            kwargs["OPF_FLOW_LIM"] = 2

        ppopt = ppoption(VERBOSE=verbose, PF_DC=not ac, INIT=init, **kwargs)
        net_inner["OPF_converged"] = False
        net_inner["converged"] = False
        _add_auxiliary_elements(net_inner)

        if not ac or net_inner["_options"]["init_results"]:
            verify_results(net_inner)
        else:
            init_results(net_inner, "opf")

        ppc, ppci = _pd2ppc(net_inner)

        if not ac:
            ppci["bus"][:, VM] = 1.0
        net_inner["_ppc_opf"] = ppci

        # Add dcline constraints if needed
        if len(net_inner.dcline) > 0:
            ppci = add_userfcn(ppci, "formulation", opf_mod._add_dcline_constraints, args=net_inner)

        # Build Bf matrix for flow constraint formulation
        _, Bf, Pbusinj, Pfinj, *_ = makeBdc(ppci["bus"], ppci["branch"])
        baseMVA = ppci["baseMVA"]

        # Add our flow gate constraint
        userfcn_args = {
            "gate_branch_idx": gate_branch_idx,
            "gate_limit_pu": gate_limit_mw / baseMVA,
            "Bf": Bf,
            "Pfinj": Pfinj,
        }
        ppci = add_userfcn(ppci, "formulation", _add_flowgate_constraint, args=userfcn_args)

        if init == "pf":
            ppci = opf_mod._run_pf_before_opf(net_inner, ppci)

        if suppress_warnings:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = opf(ppci, ppopt)
        else:
            result = opf(ppci, ppopt)

        # Capture the full result
        captured_result["f"] = result.get("f")
        captured_result["success"] = result.get("success")
        if "lin" in result:
            captured_result["lin"] = result["lin"]

        if not result["success"]:
            raise OPFNotConverged("Optimal Power Flow did not converge!")

        mode = net_inner["_options"]["mode"]
        result = _copy_results_ppci_to_ppc(result, ppc, mode=mode)

        net_inner["OPF_converged"] = True
        _extract_results(net_inner, result)
        _clean_up(net_inner)

    _saved = run_mod._optimal_powerflow
    run_mod._optimal_powerflow = _custom_optimal_powerflow

    converged = False
    objective = None
    flowgate_dual = None

    try:
        pp.rundcopp(net)
        converged = net.OPF_converged
        objective = float(net.res_cost)

        if "lin" in captured_result and "mu" in captured_result["lin"]:
            lin_mu = captured_result["lin"]["mu"]
            if "flowgate" in lin_mu.get("l", {}) and "flowgate" in lin_mu.get("u", {}):
                mu_l = float(lin_mu["l"]["flowgate"][0])
                mu_u = float(lin_mu["u"]["flowgate"][0])
                # Dual = mu_u (upper bound shadow price) - mu_l (lower bound)
                # For a binding upper constraint: mu_u > 0, mu_l = 0
                # For a binding lower constraint: mu_l > 0, mu_u = 0
                flowgate_dual = mu_u - mu_l
    except Exception:
        pass
    finally:
        run_mod._optimal_powerflow = _saved

    return converged, objective, flowgate_dual, captured_result


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute the test and return structured results."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandapower as pp

        if timeseries_dir is None:
            results["errors"].append("timeseries_dir is required for B-1")
            return results

        # ---- STEP 1: Baseline DC OPF (no flow gate) ----
        net_baseline = load_pandapower(network_file)
        _setup_dcopf(net_baseline, timeseries_dir)
        pp.rundcopp(net_baseline)
        if not net_baseline.OPF_converged:
            results["errors"].append("Baseline DC OPF did not converge")
            return results

        baseline_obj = float(net_baseline.res_cost)
        results["details"]["baseline_objective"] = baseline_obj

        # Identify gate branch: highest absolute flow
        ppc_b = net_baseline._ppc
        pf_col = ppc_b["branch"][:, 13]  # PF column (MW)
        gate_branch_idx = int(np.argmax(np.abs(pf_col)))
        unconstrained_flow = float(pf_col[gate_branch_idx])
        results["details"]["gate_branch_ppc_idx"] = gate_branch_idx
        results["details"]["unconstrained_gate_flow_mw"] = unconstrained_flow

        from_bus = int(ppc_b["branch"][gate_branch_idx, 0])
        to_bus = int(ppc_b["branch"][gate_branch_idx, 1])
        results["details"]["gate_branch_from_bus"] = from_bus
        results["details"]["gate_branch_to_bus"] = to_bus

        # ---- STEP 2: Non-binding flow gate (limit = 2x unconstrained) ----
        nonbinding_limit = abs(unconstrained_flow) * 2.0
        net_nonbind = load_pandapower(network_file)
        _setup_dcopf(net_nonbind, timeseries_dir)

        nb_converged, nb_obj, nb_dual, nb_raw = _run_dcopf_with_flowgate(
            net_nonbind, gate_branch_idx, nonbinding_limit
        )

        results["details"]["nonbinding_limit_mw"] = nonbinding_limit
        results["details"]["nonbinding_converged"] = nb_converged
        results["details"]["nonbinding_objective"] = nb_obj
        results["details"]["nonbinding_dual"] = nb_dual
        results["details"]["nonbinding_captured_keys"] = list(nb_raw.keys())

        if not nb_converged:
            results["errors"].append("Non-binding constrained DC OPF did not converge")
            return results

        # ---- STEP 3: Binding flow gate (limit = 50% of unconstrained) ----
        binding_limit = abs(unconstrained_flow) * 0.50
        net_bind = load_pandapower(network_file)
        _setup_dcopf(net_bind, timeseries_dir)

        b_converged, b_obj, b_dual, b_raw = _run_dcopf_with_flowgate(
            net_bind, gate_branch_idx, binding_limit
        )

        results["details"]["binding_limit_mw"] = binding_limit
        results["details"]["binding_converged"] = b_converged
        results["details"]["binding_objective"] = b_obj
        results["details"]["binding_dual"] = b_dual
        results["details"]["binding_captured_keys"] = list(b_raw.keys())

        if not b_converged:
            results["errors"].append("Binding constrained DC OPF did not converge")
            return results

        # Verify the constrained flow respects the gate limit
        ppc_bind = net_bind._ppc
        constrained_flow = float(ppc_bind["branch"][gate_branch_idx, 13])
        results["details"]["constrained_gate_flow_mw"] = constrained_flow
        results["details"]["flow_within_limit"] = abs(constrained_flow) <= binding_limit * 1.05

        # ---- STEP 4: Check pass conditions ----
        nonbind_dual_zero = nb_dual is not None and abs(nb_dual) < 1e-6
        bind_dual_nonzero = b_dual is not None and abs(b_dual) > 1e-6
        obj_increased = b_obj is not None and b_obj > baseline_obj * 1.001

        results["details"]["nonbind_dual_is_zero"] = nonbind_dual_zero
        results["details"]["bind_dual_is_nonzero"] = bind_dual_nonzero
        results["details"]["objective_increased"] = obj_increased
        results["details"]["objective_increase_pct"] = (
            (b_obj - baseline_obj) / baseline_obj * 100
            if b_obj is not None and baseline_obj > 0
            else None
        )

        if nb_dual is None or b_dual is None:
            results["errors"].append(
                "Could not extract dual values for flow gate constraint. "
                f"Non-binding dual: {nb_dual}, Binding dual: {b_dual}"
            )

        if nonbind_dual_zero and bind_dual_nonzero and obj_increased:
            results["status"] = "qualified_pass"
            results["workarounds"].append(
                "Custom flow gate constraint injected via PYPOWER userfcn callback system "
                "(add_userfcn 'formulation' stage -> om.add_constraints). This is the documented "
                "PYPOWER extension mechanism inherited by pandapower, but pandapower itself does "
                "not document or expose it. Required: (1) replicating pandapower's internal "
                "_optimal_powerflow function to inject the userfcn callback and capture the "
                "PYPOWER result dict, (2) monkey-patching pandapower.run._optimal_powerflow "
                "to use the custom version, (3) extracting duals from result['lin']['mu'] which "
                "pandapower normally discards during result extraction back to DataFrames."
            )
        elif nonbind_dual_zero and bind_dual_nonzero:
            results["status"] = "qualified_pass"
            results["workarounds"].append(
                "Flow gate constraint and duals work correctly. Objective did not increase "
                "significantly. Same workaround approach as above."
            )
        else:
            if not nonbind_dual_zero and nb_dual is not None:
                results["errors"].append(
                    f"Non-binding constraint dual should be ~0, got: {nb_dual}"
                )
            if not bind_dual_nonzero and b_dual is not None:
                results["errors"].append(
                    f"Binding constraint dual should be nonzero, got: {b_dual}"
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
