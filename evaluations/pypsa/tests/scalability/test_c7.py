"""
Test C-7: Solver swap — repeat DC OPF (MEDIUM) with HiGHS, GLPK, SCIP

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses)
Pass condition: At least two solvers produce results. Record whether swap requires
    reformulation or just parameter change.
Tool: pypsa 1.1.2
Solvers: HiGHS, GLPK, SCIP
"""

from __future__ import annotations

import json
import resource
import time
import traceback
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"

# Solver configurations — PyPSA/linopy abstracts the solver interface
# so swapping solvers is just changing solver_name parameter
SOLVERS = {
    "highs": {
        "time_limit": 300.0,
        "presolve": "on",
        "threads": 1,
        "output_flag": True,
    },
    "glpk": {},  # GLPK uses file-based interface via linopy
    "scip": {
        "limits/time": 300.0,
    },
}


def _load_network(case_file: str) -> tuple[pypsa.Network, CaseFrames]:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    cf = CaseFrames(str(DATA_DIR / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=9999.0)
    return net, cf


def _assign_gencosts(net: pypsa.Network, cf: CaseFrames) -> None:
    """Manually assign generator costs."""
    gencost = cf.gencost.values
    for i, gen_name in enumerate(net.generators.index):
        if i < len(gencost):
            n_coeffs = int(gencost[i, 3])
            if n_coeffs >= 2:
                c1 = gencost[i, 4 + n_coeffs - 2]
                c2 = gencost[i, 4] if n_coeffs >= 3 else 0.0
                p_op = net.generators.at[gen_name, "p_set"]
                marginal = c1 + 2 * c2 * abs(p_op)
                net.generators.at[gen_name, "marginal_cost"] = max(marginal, 0.01)
            else:
                net.generators.at[gen_name, "marginal_cost"] = 1.0 + i * 0.1
        else:
            net.generators.at[gen_name, "marginal_cost"] = 1.0 + i * 0.1

    for gen_name in net.generators.index:
        if net.generators.at[gen_name, "p_nom"] <= 0:
            net.generators.at[gen_name, "p_nom"] = max(
                net.generators.at[gen_name, "p_set"] * 1.5, 10.0
            )


def run() -> dict:
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "peak_memory_mb": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import copy

        from linopy import available_solvers as detected_solvers

        results["details"]["detected_solvers"] = detected_solvers

        # 1. Load and prepare template network
        net_template, cf = _load_network("case_ACTIVSg10k.m")
        _assign_gencosts(net_template, cf)

        results["details"]["bus_count"] = len(net_template.buses)
        results["details"]["generator_count"] = len(net_template.generators)
        results["workarounds"].append("Manually assigned marginal_cost from MATPOWER gencost.")

        # 2. Solve with each solver
        solver_results = {}
        for solver_name, solver_opts in SOLVERS.items():
            solver_info = {
                "available": solver_name in detected_solvers,
                "status": "skipped",
                "wall_clock_seconds": None,
                "objective": None,
                "error": None,
                "reformulation_needed": False,
                "swap_method": "parameter change only (solver_name argument)",
            }

            if solver_name not in detected_solvers:
                solver_info["error"] = f"Solver {solver_name} not available"
                solver_results[solver_name] = solver_info
                continue

            net = copy.deepcopy(net_template)
            solve_start = time.perf_counter()
            try:
                status = net.optimize(
                    solver_name=solver_name,
                    solver_options=solver_opts,
                )
                solver_info["wall_clock_seconds"] = time.perf_counter() - solve_start
                solver_info["solver_status"] = str(status)
                obj = net.objective if hasattr(net, "objective") else None
                solver_info["objective"] = float(obj) if obj is not None else None
                solver_info["total_generation_mw"] = float(net.generators_t.p.iloc[0].sum())
                solver_info["status"] = "pass"
            except Exception as e:
                solver_info["wall_clock_seconds"] = time.perf_counter() - solve_start
                solver_info["status"] = "fail"
                solver_info["error"] = f"{type(e).__name__}: {e}"

            solver_results[solver_name] = solver_info

        results["details"]["solver_results"] = solver_results

        # 3. Analyze objective consistency
        passed_solvers = [k for k, v in solver_results.items() if v["status"] == "pass"]
        objectives = {
            k: v["objective"]
            for k, v in solver_results.items()
            if v["status"] == "pass" and v["objective"] is not None
        }

        results["details"]["solvers_passed"] = passed_solvers
        results["details"]["objectives"] = objectives

        if len(objectives) >= 2:
            vals = list(objectives.values())
            ref = vals[0]
            diffs = {k: abs(v - ref) / max(abs(ref), 1e-10) * 100 for k, v in objectives.items()}
            results["details"]["objective_diffs_pct"] = diffs
            results["details"]["objectives_consistent"] = all(d < 1.0 for d in diffs.values())

        # 4. Document swap mechanism
        results["details"]["swap_requires_reformulation"] = False
        results["details"]["swap_mechanism"] = (
            "PyPSA/linopy abstracts the solver interface. Changing solver requires "
            "only changing the solver_name parameter in net.optimize(). The LP/MIP "
            "formulation is built once by linopy and exported to each solver via its "
            "native API (HiGHS direct, GLPK via MPS file, SCIP via pyscipopt). "
            "No reformulation or model changes needed."
        )

        if len(passed_solvers) >= 2:
            results["status"] = "pass"
        elif len(passed_solvers) == 1:
            results["status"] = "qualified_pass"
            results["errors"].append(f"Only 1 solver passed: {passed_solvers}")
        else:
            results["errors"].append("No solvers passed")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        results["peak_memory_mb"] = mem_after / 1024.0

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
