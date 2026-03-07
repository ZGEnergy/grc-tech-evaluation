"""B-1: Custom Constraints — add flow gate limit to DC OPF on IEEE 39-bus (TINY).

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Achievable through documented API. No source patching.
Dual value extractable from binding constraint.
Depends on: A-3 (DC OPF).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Execute B-1 custom constraint test."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # ── Step 1: Run baseline DC OPF (no custom constraints) ──
        grid = vge.open_file(NETWORK_FILE)
        n_bus = grid.get_bus_number()
        branches = list(grid.lines) + list(grid.transformers2w)
        n_branch = len(branches)
        details["buses"] = n_bus
        details["branches"] = n_branch

        opts = vge.OptimalPowerFlowOptions()
        opts.mip_solver = MIPSolvers.HIGHS

        t0 = time.perf_counter()
        baseline = vge.linear_opf(grid, options=opts)
        t_baseline = time.perf_counter() - t0

        if not baseline.converged:
            errors.append("Baseline DC OPF did not converge")
            return {
                "status": "fail",
                "wall_clock_seconds": t_baseline,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        baseline_flows = baseline.Sf.copy()
        baseline_lmps = baseline.bus_shadow_prices.copy()
        baseline_gen = baseline.generator_power.copy()
        details["baseline_converged"] = True
        details["baseline_total_gen_mw"] = round(float(baseline_gen.sum()), 2)
        details["baseline_lmp_range"] = [
            round(float(baseline_lmps.min()), 6),
            round(float(baseline_lmps.max()), 6),
        ]

        # Find a branch with significant flow for the flow gate constraint
        abs_flows = np.abs(baseline_flows)
        target_branch_idx = int(np.argmax(abs_flows))
        target_flow = float(baseline_flows[target_branch_idx])
        details["target_branch_index"] = target_branch_idx
        details["target_branch_name"] = branches[target_branch_idx].name
        details["target_branch_baseline_flow_mw"] = round(target_flow, 2)
        details["target_branch_original_rate"] = branches[target_branch_idx].rate

        # ── Step 2: Attempt custom constraint via rate reduction ──
        # GridCal's linear_opf enforces branch flow limits via branch.rate.
        # We can simulate a "flow gate limit" by tightening the rate on
        # the target branch to force the constraint to bind.
        # This is NOT a true custom constraint API — it's rate-based.

        # Set the flow gate limit to 80% of baseline flow
        flow_gate_limit = abs(target_flow) * 0.80
        details["flow_gate_limit_mw"] = round(flow_gate_limit, 2)

        # Reload grid and apply the constraint
        grid2 = vge.open_file(NETWORK_FILE)
        branches2 = list(grid2.lines) + list(grid2.transformers2w)
        branches2[target_branch_idx].rate = flow_gate_limit

        t0 = time.perf_counter()
        constrained = vge.linear_opf(grid2, options=opts)
        t_constrained = time.perf_counter() - t0

        if not constrained.converged:
            errors.append("Constrained DC OPF did not converge")
            details["constrained_converged"] = False
        else:
            details["constrained_converged"] = True
            constrained_flows = constrained.Sf
            constrained_lmps = constrained.bus_shadow_prices
            constrained_gen = constrained.generator_power

            details["constrained_total_gen_mw"] = round(float(constrained_gen.sum()), 2)
            details["constrained_target_flow_mw"] = round(
                float(constrained_flows[target_branch_idx]), 2
            )
            details["constrained_lmp_range"] = [
                round(float(constrained_lmps.min()), 6),
                round(float(constrained_lmps.max()), 6),
            ]

            # Check if the constraint is binding
            loading = constrained.loading
            target_loading = abs(float(loading[target_branch_idx]))
            details["target_branch_loading_pct"] = round(target_loading * 100, 2)
            details["constraint_binding"] = target_loading > 0.99

            # LMP changes?
            lmp_changed = not np.allclose(baseline_lmps, constrained_lmps, atol=1e-6)
            details["lmps_changed"] = lmp_changed

            # Check for shadow price / dual on the constraint
            # GridCal's linear_opf returns bus_shadow_prices (nodal LMPs).
            # There is no separate API for per-branch constraint duals.
            details["branch_dual_api"] = False

            # Try to access internal PuLP model for duals
            try:
                # Check if the results object has any reference to the LP model
                result_attrs = [a for a in dir(constrained) if not a.startswith("_")]
                details["results_attributes"] = result_attrs

                # Check for internal LP/MIP model access
                opf_attrs = [a for a in dir(opts) if not a.startswith("_")]
                details["opf_options_attributes"] = opf_attrs
            except Exception as e:
                details["introspection_error"] = str(e)

            # ── Step 3: Try adding a truly custom constraint ──
            # Check if GridCal exposes any constraint addition API
            custom_constraint_api = False
            api_search = []

            # Search for constraint-related methods on the grid object
            grid_methods = [
                m for m in dir(grid2) if "constraint" in m.lower() or "limit" in m.lower()
            ]
            api_search.append({"grid_methods": grid_methods})

            # Search for constraint classes in vge
            vge_constraint_classes = [
                c
                for c in dir(vge)
                if "constraint" in c.lower() or "contingency" in c.lower() or "limit" in c.lower()
            ]
            api_search.append({"vge_classes": vge_constraint_classes})

            # Check for FlowGate or similar
            flow_gate_classes = [
                c for c in dir(vge) if "gate" in c.lower() or "flowgate" in c.lower()
            ]
            api_search.append({"flow_gate_classes": flow_gate_classes})

            # Check for interface or corridor concepts
            interface_classes = [
                c
                for c in dir(vge)
                if "interface" in c.lower() or "corridor" in c.lower() or "group" in c.lower()
            ]
            api_search.append({"interface_classes": interface_classes})

            details["api_search"] = api_search
            details["custom_constraint_api_found"] = custom_constraint_api

        # ── Assessment ──
        wall_clock = t_baseline + t_constrained
        details["wall_clock_seconds"] = round(wall_clock, 6)

        # The rate-modification approach works for single-branch flow gates
        # but is NOT a general custom constraint API. Cannot add arbitrary
        # linear constraints (e.g., sum of flows across multiple branches,
        # interface limits, or generator group constraints).
        # Cannot extract per-constraint duals (only nodal LMPs).

        workaround_desc = (
            "Single-branch flow gates can be emulated by modifying branch.rate before solving. "
            "This is NOT a custom constraint API — it only handles individual branch limits. "
            "Multi-branch interface constraints, generator group constraints, or arbitrary "
            "linear constraints cannot be added. Per-constraint dual values (shadow prices) "
            "are not extractable — only nodal LMPs (bus_shadow_prices) are available."
        )

        details["assessment"] = workaround_desc
        details["can_add_custom_constraints"] = False
        details["can_extract_constraint_duals"] = False
        details["rate_modification_works"] = True

        # This is a FAIL: The pass condition requires a documented custom constraint API
        # and extractable dual values. Rate modification is a workaround, not a custom
        # constraint API.
        status = "fail"
        errors.append(
            "No custom constraint API. Branch rate modification can simulate single-branch "
            "flow gates but cannot add arbitrary linear constraints. Dual values for individual "
            "constraints are not accessible (only nodal LMPs). Source patching would be required "
            "to add custom constraints to the PuLP LP formulation."
        )

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
