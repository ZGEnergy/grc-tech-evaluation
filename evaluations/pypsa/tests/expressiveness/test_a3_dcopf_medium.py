"""
Test A-3: DC OPF with gen costs and line flow limits (dcopf)

Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m, ~10000 buses)
Pass condition: Same functional checks as TINY. MEDIUM: Does not require binding
  constraints (ACTIVSg10k is ~84-85% loaded in base case — likely uncongested).
  Record: solve time, LMP range, number of binding constraints.
  Note: uses overwrite_zero_s_nom=1.0 for the 2462 zero-rated lines to avoid OPF
  infeasibility; assigns marginal costs to all 2485 generators.
Tool: PyPSA 1.1.2
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# Solver configuration
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc dict -> pypsa.

    Uses overwrite_zero_s_nom=9999.0 to set zero-rated branches to 9999 MVA
    (effectively unconstrained). ACTIVSg10k has 2462 zero-rated lines which
    carry up to ~1840 MW in the base case — 1 MVA would make OPF infeasible.
    9999 MVA ensures these lines don't bind while the real-rated lines still constrain.
    """
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
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=9999.0)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DC OPF on ACTIVSg10k network with differentiated marginal costs.

    Assigns differentiated marginal costs to all 2485 generators using a
    linspace from $10 to $100/MWh. Records solve time, LMP range, and
    number of binding branch constraints.

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
        "workarounds": [
            "Manually assigned marginal costs — import_from_pypower_ppc does not import gencost data",
            "overwrite_zero_s_nom=9999.0 used to replace 2462 zero-rated lines with 9999 MVA "
            "(effectively unconstrained) — 1 MVA would cause OPF infeasibility since base-case "
            "flows exceed 1 MVA on these branches. Real-rated lines still constrain normally.",
        ],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        load_start = time.perf_counter()
        n = load_network(network_file)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["load_seconds"] = load_elapsed
        print(
            f"Network loaded: {len(n.buses)} buses, {len(n.generators)} generators in {load_elapsed:.3f}s"
        )

        # 2. Assign differentiated marginal costs to all generators
        gen_names = sorted(n.generators.index)
        n_gens = len(gen_names)
        costs = np.linspace(10, 100, n_gens)
        cost_map = {name: float(cost) for name, cost in zip(gen_names, costs)}
        for gen_name, cost in cost_map.items():
            n.generators.at[gen_name, "marginal_cost"] = cost

        results["details"]["n_generators_with_costs"] = n_gens
        results["details"]["cost_range"] = [float(costs.min()), float(costs.max())]
        print(
            f"Assigned marginal costs to {n_gens} generators: ${costs.min():.1f}-${costs.max():.1f}/MWh"
        )

        # 3. Check branch limits — ACTIVSg10k has 2462 zero-rated lines, handled by overwrite_zero_s_nom
        n_zero_s_nom_lines = (n.lines.s_nom >= 9998.0).sum()
        n_zero_s_nom_xfmr = (n.transformers.s_nom >= 9998.0).sum() if len(n.transformers) > 0 else 0
        results["details"]["n_lines_at_9999mva_capacity"] = int(n_zero_s_nom_lines)
        results["details"]["n_transformers_at_9999mva_capacity"] = int(n_zero_s_nom_xfmr)
        print(f"Lines with s_nom = 9999 MVA (from zero-rated): {n_zero_s_nom_lines}")

        # 4. Run DC OPF with memory tracking
        print("\n=== Running DC OPF (HiGHS LP) ===")
        tracemalloc.start()
        solve_start = time.perf_counter()
        status, condition = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        solve_elapsed = time.perf_counter() - solve_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)
        results["details"]["solver_status"] = str(status)
        results["details"]["solver_condition"] = str(condition)
        print(f"OPF solve time: {solve_elapsed:.3f}s")
        print(f"Solver status: {status}, condition: {condition}")
        print(f"Peak memory: {peak_mem / (1024 * 1024):.1f} MB")

        if str(status).lower() not in ("ok", "optimal"):
            results["errors"].append(f"OPF solver status: {status}, condition: {condition}")
            results["status"] = "fail"
            return results

        # 5. Extract LMPs
        lmps = n.buses_t.marginal_price
        assert isinstance(lmps, pd.DataFrame), "LMPs should be DataFrame"
        lmp_vals = lmps.iloc[0]
        lmp_max = float(lmp_vals.max())
        lmp_min = float(lmp_vals.min())
        lmp_mean = float(lmp_vals.mean())
        lmp_spread = lmp_max - lmp_min
        n_unique_lmps = int(lmp_vals.nunique())

        results["details"]["lmp_min"] = lmp_min
        results["details"]["lmp_max"] = lmp_max
        results["details"]["lmp_mean"] = lmp_mean
        results["details"]["lmp_spread"] = lmp_spread
        results["details"]["n_unique_lmps"] = n_unique_lmps
        results["details"]["lmp_first5"] = lmp_vals.head(5).to_dict()

        print("\n=== LMP Statistics ===")
        print(f"  Min: ${lmp_min:.2f}/MWh, Max: ${lmp_max:.2f}/MWh")
        print(f"  Mean: ${lmp_mean:.2f}/MWh, Spread: ${lmp_spread:.2f}/MWh")
        print(f"  Unique LMP values: {n_unique_lmps} (uniform = uncongested)")
        print("  First 5 bus LMPs:")
        print(lmp_vals.head(5).to_string())

        # 6. Extract optimal dispatch
        gen_dispatch = n.generators_t.p
        dispatch_vals = gen_dispatch.iloc[0] if len(gen_dispatch) > 0 else pd.Series()
        total_gen = float(dispatch_vals.sum()) if len(dispatch_vals) > 0 else 0.0
        total_load = float(n.loads.p_set.sum())
        results["details"]["total_generation_mw"] = total_gen
        results["details"]["total_load_mw"] = total_load
        results["details"]["objective_value"] = (
            float(n.objective) if hasattr(n, "objective") else None
        )
        print("\n=== Dispatch Summary ===")
        print(f"  Total generation: {total_gen:.1f} MW, Total load: {total_load:.1f} MW")
        if hasattr(n, "objective"):
            print(f"  Objective: ${n.objective:.0f}/h")

        # 7. Check for binding branch constraints via linopy model
        binding_lines = []
        binding_transformers = []

        try:
            if hasattr(n, "model") and n.model is not None:
                constraint_names = list(n.model.constraints)
                results["details"]["available_constraints"] = constraint_names

                for cname in ["Line-fix-s-upper", "Line-fix-s-lower"]:
                    if cname in n.model.constraints:
                        dual_da = n.model.constraints[cname].dual
                        if dual_da is not None:
                            vals_flat = dual_da.values.flatten()
                            nonzero_idx = np.where(abs(vals_flat) > 1e-6)[0]
                            if len(nonzero_idx) > 0:
                                names_coord = dual_da.coords["name"].values
                                for idx in nonzero_idx:
                                    if idx < len(names_coord):
                                        line_name = str(names_coord[idx])
                                        if line_name not in binding_lines:
                                            binding_lines.append(line_name)

                for cname in ["Transformer-fix-s-upper", "Transformer-fix-s-lower"]:
                    if cname in n.model.constraints:
                        dual_da = n.model.constraints[cname].dual
                        if dual_da is not None:
                            vals_flat = dual_da.values.flatten()
                            nonzero_idx = np.where(abs(vals_flat) > 1e-6)[0]
                            if len(nonzero_idx) > 0:
                                names_coord = dual_da.coords["name"].values
                                for idx in nonzero_idx:
                                    if idx < len(names_coord):
                                        t_name = str(names_coord[idx])
                                        if t_name not in binding_transformers:
                                            binding_transformers.append(t_name)

        except Exception as model_err:
            results["errors"].append(f"Model constraint extraction issue: {model_err}")

        n_binding_total = len(binding_lines) + len(binding_transformers)
        results["details"]["binding_lines"] = binding_lines[:20]  # cap output size
        results["details"]["n_binding_lines"] = len(binding_lines)
        results["details"]["n_binding_transformers"] = len(binding_transformers)
        results["details"]["n_binding_total"] = n_binding_total
        results["details"]["shadow_price_source"] = (
            "n.model.constraints (linopy model) — n.lines_t.mu_upper not populated in v1.1.2"
        )
        print("\n=== Binding Branch Constraints ===")
        print(f"  Lines: {len(binding_lines)}, Transformers: {len(binding_transformers)}")
        print(f"  Total binding: {n_binding_total}")
        if n_unique_lmps == 1:
            print("  NOTE: Uniform LMPs suggest uncongested network (no binding flow limits)")

        # Also check by utilization ratio
        if len(n.lines_t.p0) > 0:
            p0_vals = n.lines_t.p0.iloc[0]
            s_nom_vals = n.lines.s_nom
            utilization = (p0_vals.abs() / s_nom_vals.reindex(p0_vals.index)).fillna(0)
            n_near_binding = int((utilization > 0.99).sum())
            results["details"]["n_lines_near_binding_by_flow"] = n_near_binding
            print(f"  Lines >99% utilization: {n_near_binding}")

        results["workarounds"].append(
            "Shadow prices extracted from n.model.constraints (linopy model) rather than "
            "n.lines_t.mu_upper — the latter is empty after n.optimize() in v1.1.2. "
            "This is fragile: depends on internal constraint naming convention."
        )

        # 8. Pass condition
        # On MEDIUM: binding constraints NOT required (network may be uncongested).
        # Pass requires: solver optimal, LMPs accessible, dispatch accessible.
        if str(status).lower() in ("ok", "optimal"):
            # Qualified pass because of fragile shadow price extraction workaround
            results["status"] = "qualified_pass"
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
