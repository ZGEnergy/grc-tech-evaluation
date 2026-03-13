"""
Test A-3: DC OPF with gen costs and line flow limits (dcopf)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable from
  solution. With differentiated costs and 70% derating of ALL branch flow limits,
  at least 2 branches have non-zero shadow prices (binding flow constraints).
  Report max LMP spread across buses.
Tool: PyPSA 1.1.2
"""

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")


def load_network(network_file: str):
    """Load case39.m via matpowercaseframes -> pypower ppc dict -> pypsa."""
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
    return n


# Solver configuration (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DC OPF with differentiated marginal costs and derated branch limits.

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
        # 1. Load network
        n = load_network(network_file)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["base_power_mva"] = (
            n.meta.get("baseMVA", 100.0) if hasattr(n, "meta") else 100.0
        )

        results["workarounds"].append(
            "Manually assigned marginal costs — import_from_pypower_ppc does not import gencost"
        )

        # 2. Assign differentiated marginal costs
        # Generators sorted by index, assign ascending costs: gen1=10, gen2=20, ... gen10=100 $/MWh
        gen_names = sorted(n.generators.index)
        n_gens = len(gen_names)
        # Differentiated costs from $10 to $100 in equal steps
        costs = np.linspace(10, 100, n_gens)
        cost_map = {name: float(cost) for name, cost in zip(gen_names, costs)}

        for gen_name, cost in cost_map.items():
            n.generators.at[gen_name, "marginal_cost"] = cost

        results["details"]["marginal_costs"] = cost_map
        results["details"]["n_generators_with_costs"] = len(cost_map)

        # 3. Derate ALL branch flow limits by 70%
        original_s_nom = n.lines.s_nom.copy()
        n.lines.s_nom = n.lines.s_nom * 0.7

        # Store original/derated for reporting
        n_lines_derated = (n.lines.s_nom > 0).sum()
        results["details"]["lines_derated_count"] = int(n_lines_derated)
        results["details"]["original_s_nom_max"] = float(original_s_nom.max())
        results["details"]["derated_s_nom_max"] = float(n.lines.s_nom.max())

        # Also derate transformers if present
        if len(n.transformers) > 0:
            n.transformers.s_nom = n.transformers.s_nom * 0.7
            results["details"]["transformers_derated"] = len(n.transformers)

        # 4. Run DC OPF
        solve_start = time.perf_counter()
        status, condition = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        solve_elapsed = time.perf_counter() - solve_start
        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["solver_status"] = str(status)
        results["details"]["solver_condition"] = str(condition)

        if str(status).lower() not in ("ok", "optimal"):
            results["errors"].append(f"OPF solver status: {status}, condition: {condition}")
            results["status"] = "fail"
            return results

        # 5. Extract LMPs (marginal prices at each bus)
        lmps = n.buses_t.marginal_price
        assert isinstance(lmps, pd.DataFrame), "LMPs should be DataFrame"
        assert len(lmps) > 0, "LMPs are empty"

        lmp_vals = lmps.iloc[0]
        lmp_max = float(lmp_vals.max())
        lmp_min = float(lmp_vals.min())
        lmp_spread = lmp_max - lmp_min

        results["details"]["lmp_values"] = lmp_vals.to_dict()
        results["details"]["lmp_max"] = lmp_max
        results["details"]["lmp_min"] = lmp_min
        results["details"]["lmp_spread"] = lmp_spread

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
        # PyPSA v1.1.2: n.lines_t.mu_upper is NOT populated after optimize()
        # Must extract from n.model.constraints directly (linopy model constraints)
        binding_lines = []
        binding_transformers = []
        n_binding_total = 0

        # Primary method: n.lines_t.mu_upper (populated by some PyPSA versions)
        mu_upper = n.lines_t.mu_upper
        mu_lower = n.lines_t.mu_lower
        if len(mu_upper) > 0 and len(mu_upper.columns) > 0:
            mu_upper_vals = mu_upper.iloc[0].abs()
            mu_lower_vals = (
                mu_lower.iloc[0].abs()
                if len(mu_lower) > 0
                else pd.Series(0, index=mu_upper.columns)
            )
            mu_combined = mu_upper_vals + mu_lower_vals
            binding_mask = mu_combined > 1e-6
            binding_lines = list(mu_combined[binding_mask].index)
            results["details"]["mu_upper_nonzero"] = mu_upper_vals[mu_upper_vals > 1e-6].to_dict()

        # Secondary method: extract from linopy model constraints (documented public API)
        # This is the reliable approach in v1.1.2
        try:
            if hasattr(n, "model") and n.model is not None:
                print("\nAvailable model constraints:", list(n.model.constraints))
                # Line capacity constraints
                for cname in ["Line-fix-s-upper", "Line-fix-s-lower"]:
                    if cname in n.model.constraints:
                        dual_da = n.model.constraints[cname].dual
                        if dual_da is not None:
                            vals_flat = dual_da.values.flatten()
                            nonzero_idx = np.where(abs(vals_flat) > 1e-6)[0]
                            if len(nonzero_idx) > 0:
                                # Get line names from coordinate
                                names_coord = dual_da.coords["name"].values
                                for idx in nonzero_idx:
                                    if idx < len(names_coord):
                                        line_name = str(names_coord[idx])
                                        dual_val = float(vals_flat[idx])
                                        if line_name not in binding_lines:
                                            binding_lines.append(line_name)
                                        print(f"  {cname}[{line_name}] = {dual_val:.4f}")

                # Transformer capacity constraints
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
                                        print(f"  {cname}[{t_name}] = {float(vals_flat[idx]):.4f}")
        except Exception as model_err:
            results["errors"].append(f"Model constraint extraction issue: {model_err}")

        n_binding_total = len(binding_lines) + len(binding_transformers)
        results["details"]["binding_lines"] = binding_lines
        results["details"]["binding_transformers"] = binding_transformers
        results["details"]["n_binding_constraints"] = n_binding_total
        results["details"]["shadow_price_source"] = (
            "n.model.constraints (linopy model, not n.lines_t.mu_upper — "
            "mu_upper not populated in PyPSA v1.1.2 after optimize())"
        )
        print(
            f"\n=== Binding Branch Constraints: {len(binding_lines)} lines + {len(binding_transformers)} transformers ==="
        )
        results["workarounds"].append(
            "Shadow prices extracted from n.model.constraints (linopy model) rather than "
            "n.lines_t.mu_upper — the latter is empty after n.optimize() in v1.1.2. "
            "This is fragile: depends on undocumented internal constraint naming convention "
            "('Line-fix-s-upper', 'Line-fix-s-lower')."
        )

        # Check line flows too
        p0_vals = n.lines_t.p0.iloc[0] if len(n.lines_t.p0) > 0 else pd.Series()
        s_nom_vals = n.lines.s_nom
        if len(p0_vals) > 0:
            utilization = (p0_vals.abs() / s_nom_vals).fillna(0)
            n_near_binding = (utilization > 0.95).sum()
            results["details"]["n_lines_near_binding_by_flow"] = int(n_near_binding)
            print(f"\nLines with >95% utilization: {n_near_binding}")
            print(utilization.nlargest(5).to_string())

        # 8. Pass condition check
        # Shadow prices accessible via linopy model constraints (fragile workaround)
        n_binding = results["details"].get("n_binding_constraints", 0)
        if n_binding < 2:
            results["errors"].append(
                f"Only {n_binding} binding branch constraints found (need >= 2)."
            )
            results["status"] = "fail"
        else:
            # Pass condition met: >= 2 binding, but required fragile workaround
            # to access shadow prices (n.model.constraints vs n.lines_t.mu_upper)
            results["status"] = "qualified_pass"

        # Save full dispatch for A-4 reference
        results["details"]["dispatch_full"] = dispatch_vals.to_dict()
        results["details"]["lmps_full"] = lmp_vals.to_dict()

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
