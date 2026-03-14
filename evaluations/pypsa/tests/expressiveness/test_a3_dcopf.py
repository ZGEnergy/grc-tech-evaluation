"""
Test A-3: Solve DC OPF with gen costs and line flow limits on TINY (Modified Tiny data)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable from solution.
  With differentiated costs and 70% derating, at least 2 branches have non-zero
  shadow prices (binding flow constraints). Report max LMP spread across buses.
Solver: HiGHS
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
    "output_flag": True,
}

# Cost map from gen_temporal_params.csv / README (tech_class_key -> $/MWh)
COST_MAP = {
    "hydro": 5.0,
    "nuclear": 10.0,
    "coal_large": 25.0,
    "gas_CC": 40.0,
}


def run(
    network_file: str = DEFAULT_NETWORK,
    timeseries_dir: str | None = DEFAULT_TIMESERIES,
) -> dict:
    """Execute DC OPF with Modified Tiny data: differentiated costs + 70% branch derating.

    Returns:
        dict with standard keys (status, wall_clock_seconds, details, errors, workarounds)
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
        # 1. Load network via shared loader
        from matpower_loader import load_pypsa

        n = load_pypsa(network_file)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        results["details"]["n_generators"] = len(n.generators)

        # 2. Apply Modified Tiny: differentiated generator costs from gen_temporal_params.csv
        if timeseries_dir is None:
            results["errors"].append("timeseries_dir is required for Modified Tiny data")
            return results

        ts_dir = Path(timeseries_dir)
        gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")
        results["details"]["gen_params_loaded"] = len(gen_params)

        # Map gen_index (0-based MATPOWER order) to PyPSA generator names
        gen_names = n.generators.index.tolist()
        cost_assignments = {}

        for _, row in gen_params.iterrows():
            gen_idx = int(row["gen_index"])
            tech_key = row["tech_class_key"]
            if gen_idx < len(gen_names):
                gen_name = gen_names[gen_idx]
                mc = COST_MAP.get(tech_key, 30.0)  # fallback if unknown
                n.generators.at[gen_name, "marginal_cost"] = mc
                cost_assignments[gen_name] = {
                    "tech_class": tech_key,
                    "marginal_cost": mc,
                }

        results["details"]["cost_assignments"] = cost_assignments
        results["details"]["n_generators_with_costs"] = len(cost_assignments)

        # Verify cost differentiation
        unique_costs = set(v["marginal_cost"] for v in cost_assignments.values())
        results["details"]["n_unique_cost_levels"] = len(unique_costs)
        results["details"]["cost_levels"] = sorted(unique_costs)

        # 3. Derate ALL branch flow limits by 70%
        original_s_nom_lines = n.lines.s_nom.copy()
        n.lines.s_nom = n.lines.s_nom * 0.7
        results["details"]["lines_derated_count"] = int((n.lines.s_nom > 0).sum())
        results["details"]["original_s_nom_max"] = float(original_s_nom_lines.max())
        results["details"]["derated_s_nom_max"] = float(n.lines.s_nom.max())

        if len(n.transformers) > 0:
            n.transformers.s_nom = n.transformers.s_nom * 0.7
            results["details"]["transformers_derated"] = len(n.transformers)

        # 4. Run DC OPF
        import tracemalloc

        tracemalloc.start()
        solve_start = time.perf_counter()
        status, condition = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        solve_elapsed = time.perf_counter() - solve_start
        _current, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)
        results["details"]["solver_status"] = str(status)
        results["details"]["solver_condition"] = str(condition)
        results["details"]["solver_name"] = SOLVER_NAME

        if str(status).lower() not in ("ok", "optimal"):
            results["errors"].append(f"OPF solver status: {status}, condition: {condition}")
            return results

        # 5. Extract LMPs (marginal prices at each bus)
        lmps = n.buses_t.marginal_price
        assert isinstance(lmps, pd.DataFrame), "LMPs should be DataFrame"
        assert len(lmps) > 0, "LMPs are empty"

        lmp_vals = lmps.iloc[0]
        lmp_max = float(lmp_vals.max())
        lmp_min = float(lmp_vals.min())
        lmp_spread = lmp_max - lmp_min

        results["details"]["lmp_max"] = lmp_max
        results["details"]["lmp_min"] = lmp_min
        results["details"]["lmp_spread"] = lmp_spread
        results["details"]["lmp_values"] = lmp_vals.to_dict()

        print("=== LMPs ($/MWh) — all buses ===")
        print(lmp_vals.to_string())

        # 6. Extract optimal dispatch
        gen_dispatch = n.generators_t.p
        assert isinstance(gen_dispatch, pd.DataFrame), "gen_dispatch should be DataFrame"
        dispatch_vals = gen_dispatch.iloc[0]
        total_gen = float(dispatch_vals.sum())
        total_load = float(n.loads.p_set.sum())

        results["details"]["dispatch_mw"] = dispatch_vals.to_dict()
        results["details"]["total_generation_mw"] = total_gen
        results["details"]["total_load_mw"] = total_load
        results["details"]["objective_value"] = (
            float(n.objective) if hasattr(n, "objective") else None
        )

        print("\n=== Optimal Dispatch (MW) ===")
        print(dispatch_vals.to_string())

        # 7. Check for binding branch constraints (shadow prices)
        # Extract from linopy model constraints
        binding_branches = []
        shadow_prices = {}

        try:
            if hasattr(n, "model") and n.model is not None:
                constraint_names = list(n.model.constraints)
                results["details"]["model_constraint_names"] = constraint_names

                for cname in constraint_names:
                    if "fix-s-upper" in cname or "fix-s-lower" in cname:
                        dual_da = n.model.constraints[cname].dual
                        if dual_da is not None:
                            vals_flat = dual_da.values.flatten()
                            nonzero_mask = np.abs(vals_flat) > 1e-6
                            if nonzero_mask.any():
                                if "name" in dual_da.coords:
                                    names = dual_da.coords["name"].values
                                elif "Line" in dual_da.dims or "Transformer" in dual_da.dims:
                                    dim_name = [d for d in dual_da.dims if d != "snapshot"]
                                    names = dual_da.coords[dim_name[0]].values if dim_name else []
                                else:
                                    names = []

                                for idx in np.where(nonzero_mask)[0]:
                                    if idx < len(names):
                                        name = str(names[idx])
                                        dual_val = float(vals_flat[idx])
                                        binding_branches.append(name)
                                        shadow_prices[name] = dual_val
                                        print(f"  {cname}[{name}] = {dual_val:.4f}")
        except Exception as model_err:
            results["errors"].append(f"Model constraint extraction issue: {model_err}")

        # Also check via line utilization
        if len(n.lines_t.p0) > 0:
            p0_vals = n.lines_t.p0.iloc[0]
            utilization = (
                (p0_vals.abs() / n.lines.s_nom).replace([np.inf, -np.inf], np.nan).fillna(0)
            )
            n_near_binding = int((utilization > 0.95).sum())
            results["details"]["n_lines_near_binding_by_flow"] = n_near_binding
            results["details"]["top5_utilization"] = utilization.nlargest(5).to_dict()
            print(f"\nLines with >95% utilization: {n_near_binding}")
            print(utilization.nlargest(5).to_string())

        # Also check mu_upper/mu_lower in case PyPSA populates them
        mu_upper = n.lines_t.mu_upper
        if len(mu_upper) > 0 and len(mu_upper.columns) > 0:
            mu_vals = mu_upper.iloc[0].abs()
            mu_binding = mu_vals[mu_vals > 1e-6]
            if len(mu_binding) > 0:
                results["details"]["mu_upper_nonzero"] = mu_binding.to_dict()
                for name in mu_binding.index:
                    if name not in binding_branches:
                        binding_branches.append(name)
                        shadow_prices[name] = float(mu_binding[name])

        n_binding = len(binding_branches)
        results["details"]["binding_branches"] = binding_branches
        results["details"]["shadow_prices"] = shadow_prices
        results["details"]["n_binding_constraints"] = n_binding

        print(f"\n=== Binding Constraints: {n_binding} branches ===")

        # 8. Pass condition check
        if n_binding < 2:
            results["errors"].append(
                f"Only {n_binding} binding branch constraints found (need >= 2). "
                f"LMP spread: {lmp_spread:.2f} $/MWh"
            )
            results["status"] = "fail"
        else:
            # Shadow prices were extracted from linopy model constraints
            # This uses documented linopy API on the model object
            results["workarounds"].append(
                "Shadow prices extracted from n.model.constraints (linopy dual values) "
                "rather than n.lines_t.mu_upper. The mu_upper/mu_lower DataFrames may "
                "be empty after n.optimize() in PyPSA v1.1.2; the linopy model's "
                "constraint duals provide the same information via public linopy API."
            )
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
