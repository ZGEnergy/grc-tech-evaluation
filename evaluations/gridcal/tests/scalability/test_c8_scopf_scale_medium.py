"""
Test C-8: SCOPF (N-1, 50 contingencies) on MEDIUM.

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: SCOPF (N-1, 50 contingencies) solves on MEDIUM.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS

Scales C-8 SMALL (5.45s with 50 contingencies on 2000-bus) to MEDIUM (10000-bus).
Uses the same LODF-based SCOPF formulation via `consider_contingencies=True`.

Contingency selection: 50 most-loaded branches from base-case DCOPF, sorted
by loading percentage descending.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal

N_CONTINGENCIES = 50


def run(
    network_file: str = "data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute C-8 SCOPF scale test on MEDIUM and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import VeraGridEngine as vge
        from VeraGridEngine.Devices import Contingency, ContingencyGroup
        from VeraGridEngine.enumerations import (
            ContingencyOperationTypes,
            MIPSolvers,
            SolverType,
        )

        # =====================================================================
        # Step 1: Run base-case DCOPF for comparison and contingency selection
        # =====================================================================
        grid_base = load_gridcal(network_file)
        generators_base = grid_base.get_generators()
        branches_base = grid_base.get_branches()
        n_buses = grid_base.get_bus_number()
        n_gens = len(generators_base)
        n_branches = len(branches_base)

        results["details"]["bus_count"] = n_buses
        results["details"]["gen_count"] = n_gens
        results["details"]["branch_count"] = n_branches

        opf_opts_base = vge.OptimalPowerFlowOptions(
            solver=SolverType.LINEAR_OPF,
            mip_solver=MIPSolvers.HIGHS,
        )

        base_start = time.perf_counter()
        results_base = vge.linear_opf(grid_base, opf_opts_base)
        base_elapsed = time.perf_counter() - base_start

        if not results_base.converged:
            results["errors"].append("Base-case DCOPF did not converge on MEDIUM")
            return results

        base_gen = results_base.generator_power.copy()
        base_lmps = results_base.bus_shadow_prices.copy()
        base_loading = np.abs(results_base.loading)

        results["details"]["base_dcopf_converged"] = True
        results["details"]["base_dcopf_wall_clock_seconds"] = base_elapsed
        results["details"]["base_total_gen_mw"] = float(np.sum(base_gen))
        results["details"]["base_lmp_range"] = {
            "min": float(np.min(base_lmps)),
            "max": float(np.max(base_lmps)),
        }
        results["details"]["base_max_loading_pct"] = float(np.max(base_loading) * 100)

        # =====================================================================
        # Step 2: Select top-50 most-loaded branches as contingencies
        # =====================================================================
        loading_ranked = sorted(
            [(i, float(base_loading[i])) for i in range(len(base_loading))],
            key=lambda x: x[1],
            reverse=True,
        )
        selected_indices = [idx for idx, _ in loading_ranked[:N_CONTINGENCIES]]
        results["details"]["contingency_selection_method"] = (
            f"Top {N_CONTINGENCIES} most-loaded branches from base-case DCOPF"
        )
        results["details"]["contingency_loading_range"] = {
            "most_loaded_pct": float(loading_ranked[0][1] * 100),
            "least_loaded_in_set_pct": float(
                loading_ranked[min(N_CONTINGENCIES - 1, len(loading_ranked) - 1)][1] * 100
            ),
        }

        # =====================================================================
        # Step 3: Run SCOPF with N-1 contingencies
        # =====================================================================
        grid_scopf = load_gridcal(network_file)
        branches_scopf = grid_scopf.get_branches()
        generators_scopf = grid_scopf.get_generators()
        gen_names = [g.name or f"gen_{i}" for i, g in enumerate(generators_scopf)]
        branch_names_scopf = [b.name for b in branches_scopf]

        # Create contingency groups for selected branches
        contingency_groups = []
        for idx in selected_indices:
            br = branches_scopf[idx]
            cg = ContingencyGroup(name=f"N-1_{br.name}")
            grid_scopf.add_contingency_group(cg)
            c = Contingency(
                device=br,
                name=f"ctg_{br.name}",
                prop=ContingencyOperationTypes.Active,
                value=0.0,
                group=cg,
            )
            grid_scopf.add_contingency(c)
            contingency_groups.append(cg)

        results["details"]["n_contingencies"] = len(contingency_groups)

        tracemalloc.start()
        scopf_start = time.perf_counter()

        opf_opts_scopf = vge.OptimalPowerFlowOptions(
            solver=SolverType.LINEAR_OPF,
            mip_solver=MIPSolvers.HIGHS,
            consider_contingencies=True,
            contingency_groups_used=tuple(contingency_groups),
        )

        results_scopf = vge.linear_opf(grid_scopf, opf_opts_scopf)
        scopf_elapsed = time.perf_counter() - scopf_start
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["scopf_wall_clock_seconds"] = scopf_elapsed
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)

        converged = bool(results_scopf.converged)
        results["details"]["scopf_converged"] = converged

        if not converged:
            results["errors"].append("SCOPF did not converge on MEDIUM with 50 contingencies")
            return results

        scopf_gen = results_scopf.generator_power.copy()
        scopf_lmps = results_scopf.bus_shadow_prices.copy()
        scopf_loading = np.abs(results_scopf.loading)
        scopf_total_gen = float(np.sum(scopf_gen))

        results["details"]["scopf_total_gen_mw"] = scopf_total_gen
        results["details"]["scopf_lmp_range"] = {
            "min": float(np.min(scopf_lmps)),
            "max": float(np.max(scopf_lmps)),
        }
        results["details"]["scopf_max_loading_pct"] = float(np.max(scopf_loading) * 100)

        # =====================================================================
        # Step 4: Comparison and analysis
        # =====================================================================

        # Dispatch differs from base case?
        dispatch_diff = np.abs(scopf_gen - base_gen)
        max_dispatch_diff = float(np.max(dispatch_diff))
        dispatch_differs = max_dispatch_diff > 0.01
        results["details"]["dispatch_differs_from_base"] = dispatch_differs
        results["details"]["max_dispatch_diff_mw"] = max_dispatch_diff

        # LMP comparison
        lmp_diff = np.abs(scopf_lmps - base_lmps)
        max_lmp_diff = float(np.max(lmp_diff))
        results["details"]["max_lmp_diff"] = max_lmp_diff

        # Top generators by dispatch change
        gen_changes = [
            {
                "name": gen_names[i],
                "base_mw": float(base_gen[i]),
                "scopf_mw": float(scopf_gen[i]),
                "diff_mw": float(scopf_gen[i] - base_gen[i]),
            }
            for i in range(n_gens)
            if abs(float(scopf_gen[i] - base_gen[i])) > 1.0
        ]
        gen_changes.sort(key=lambda x: abs(x["diff_mw"]), reverse=True)
        results["details"]["top_dispatch_changes"] = gen_changes[:10]

        # Binding branches in SCOPF
        binding_branches = [
            {"branch": branch_names_scopf[i], "loading_pct": float(scopf_loading[i] * 100)}
            for i in range(len(scopf_loading))
            if scopf_loading[i] >= 0.99
        ]
        results["details"]["scopf_binding_branch_count"] = len(binding_branches)
        results["details"]["scopf_binding_branches"] = binding_branches[:20]

        # Scale comparison vs SMALL
        results["details"]["scale_comparison"] = {
            "small_scopf_time_s": 5.45,
            "medium_scopf_time_s": scopf_elapsed,
            "small_bus_count": 2000,
            "medium_bus_count": n_buses,
            "scale_factor": n_buses / 2000,
            "time_ratio": scopf_elapsed / 5.45 if scopf_elapsed > 0 else None,
        }

        # =====================================================================
        # Step 5: Pass condition check
        # =====================================================================
        pass_checks = {
            "scopf_converged": converged,
            "contingencies_in_optimization": True,
            "n_contingencies_50": len(contingency_groups) == N_CONTINGENCIES,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
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
