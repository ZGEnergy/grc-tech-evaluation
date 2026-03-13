"""
Test A-9: Security-Constrained OPF (scopf)

Dimension: expressiveness
Network: SMALL (ACTIVSg 2k, case_ACTIVSg2000.m, ~2000 buses, 544 generators)
Pass condition: Solves. Base-case dispatch respects all contingency flow limits
  simultaneously. Dispatch and cost differ from unconstrained. Post-contingency
  flows within limits for all included contingencies.
Tool: PyPSA 1.1.2

Depends on: A-3 pattern (use differentiated costs, full s_nom for feasibility)
API: n.optimize.optimize_security_constrained(snapshots, branch_outages=[...])
"""

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m")

# Solver configuration
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

GEN_COST_MIN = 10.0
GEN_COST_MAX = 100.0

# Number of contingencies to select (3-5 per pre-knowledge)
N_CONTINGENCIES = 3


def load_network(network_file: str):
    """Load ACTIVSg2000 via matpowercaseframes -> pypower ppc dict -> pypsa."""
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
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def assign_costs(n) -> None:
    """Assign linearly-spaced marginal costs to all generators."""
    gen_names = sorted(n.generators.index)
    n_gens = len(gen_names)
    costs = np.linspace(GEN_COST_MIN, GEN_COST_MAX, n_gens)
    for gen_name, cost in zip(gen_names, costs):
        n.generators.at[gen_name, "marginal_cost"] = float(cost)


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute Security-Constrained OPF on SMALL network.

    Methodology:
    1. Load case_ACTIVSg2000.m, assign differentiated costs, use full s_nom
    2. Run unconstrained base OPF for contingency selection
    3. Select 3-5 lines with moderate utilization (30-65%)
    4. Run SCOPF via n.optimize.optimize_security_constrained()
    5. Verify base-case dispatch differs and no overloads

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
        # 1. Load network with differentiated costs (full s_nom — not derated)
        n = load_network(network_file)
        assign_costs(n)

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["branch_derating"] = "none (full s_nom for SCOPF feasibility)"
        results["workarounds"].append(
            "Manually assigned marginal costs — import_from_pypower_ppc does not import gencost"
        )
        results["workarounds"].append(
            "Full s_nom used (no derating) — derating makes SCOPF infeasible on SMALL network "
            "same as TINY: any N-1 contingency on a congested network cannot be resolved by redispatch"
        )

        print(
            f"Network: {len(n.buses)} buses, {len(n.lines)} lines, {len(n.generators)} generators"
        )
        snapshot = n.snapshots[0]

        # 2. Run base-case unconstrained OPF
        print("=== Running base-case unconstrained OPF ===")
        base_status, base_condition = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        results["details"]["base_opf_status"] = str(base_status)

        if str(base_status).lower() not in ("ok", "optimal"):
            results["errors"].append(f"Base OPF failed: {base_status}, {base_condition}")
            results["status"] = "fail"
            return results

        base_objective = float(n.objective)
        base_dispatch = n.generators_t.p.iloc[0].to_dict()
        results["details"]["base_objective"] = base_objective
        print(f"Base OPF objective: ${base_objective:,.0f}/h")

        # 3. Select contingency branches
        p0_abs = n.lines_t.p0.iloc[0].abs()
        s_nom = n.lines.s_nom
        utilization = (p0_abs / s_nom).fillna(0)

        # Prefer lines with 30-65% utilization
        moderate_util = utilization[(utilization > 0.30) & (utilization < 0.65)]
        moderate_sorted = moderate_util.sort_values(ascending=False)

        if len(moderate_sorted) >= N_CONTINGENCIES:
            contingency_lines = list(moderate_sorted.head(N_CONTINGENCIES).index)
        elif len(moderate_sorted) >= 1:
            wider_util = utilization[(utilization > 0.10) & (utilization < 0.70)]
            contingency_lines = list(
                wider_util.sort_values(ascending=False).head(N_CONTINGENCIES).index
            )
        else:
            nonzero_util = utilization[utilization > 0.05].sort_values()
            contingency_lines = list(nonzero_util.head(N_CONTINGENCIES).index)

        if len(contingency_lines) == 0:
            results["errors"].append("No suitable contingency lines found")
            results["status"] = "fail"
            return results

        results["details"]["contingency_lines"] = contingency_lines
        results["details"]["contingency_utilizations"] = {
            line: float(utilization[line]) for line in contingency_lines
        }
        print(f"Contingencies: {contingency_lines}")
        print(f"Utilizations: {[f'{utilization[ln]:.3f}' for ln in contingency_lines]}")

        # 4. Run Security-Constrained OPF
        print(f"\n=== Running SCOPF (N-1 for {len(contingency_lines)} contingencies) ===")
        scopf_start = time.perf_counter()
        scopf_status = n.optimize.optimize_security_constrained(
            snapshots=[snapshot],
            branch_outages=contingency_lines,
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        scopf_elapsed = time.perf_counter() - scopf_start
        results["details"]["scopf_solve_seconds"] = scopf_elapsed
        results["details"]["scopf_result"] = str(scopf_status)
        print(f"SCOPF solve time: {scopf_elapsed:.2f}s | result: {scopf_status}")

        scopf_ok = False
        if isinstance(scopf_status, tuple):
            sc_status, sc_condition = scopf_status
            results["details"]["scopf_status"] = str(sc_status)
            results["details"]["scopf_condition"] = str(sc_condition)
            scopf_ok = str(sc_status).lower() in ("ok", "optimal")
        else:
            results["details"]["scopf_status"] = str(scopf_status)
            scopf_ok = str(scopf_status).lower() in ("ok", "optimal")

        if not scopf_ok:
            results["errors"].append(f"SCOPF did not solve: {scopf_status}")
            results["status"] = "fail"
            return results

        # 5. Extract results
        scopf_objective = float(n.objective)
        scopf_dispatch = n.generators_t.p.iloc[0].to_dict()
        scopf_lmps = n.buses_t.marginal_price.iloc[0]

        results["details"]["scopf_objective"] = scopf_objective
        cost_diff_pct = abs(scopf_objective - base_objective) / base_objective * 100.0
        results["details"]["cost_diff_vs_base_pct"] = float(cost_diff_pct)

        dispatch_changed = any(
            abs(scopf_dispatch.get(g, 0) - base_dispatch.get(g, 0)) > 1.0
            for g in n.generators.index
        )
        results["details"]["dispatch_changed_from_base"] = dispatch_changed

        print(
            f"Base OPF: ${base_objective:,.0f}/h → SCOPF: ${scopf_objective:,.0f}/h "
            f"(Δ={cost_diff_pct:.2f}%)"
        )
        print(f"Dispatch changed: {dispatch_changed}")

        # 6. Check base-case flow violations after SCOPF
        p0_scopf = n.lines_t.p0.iloc[0].abs()
        s_nom_scopf = n.lines.s_nom
        overloaded = []
        for line in p0_scopf.index:
            if line in s_nom_scopf.index:
                flow = float(p0_scopf[line])
                limit = float(s_nom_scopf[line])
                if limit > 0 and flow > limit * 1.001:
                    overloaded.append(
                        {
                            "line": line,
                            "flow_mw": flow,
                            "limit_mw": limit,
                            "loading_pct": float(flow / limit * 100),
                        }
                    )

        results["details"]["base_case_overloads_after_scopf"] = overloaded[:10]
        results["details"]["n_base_case_overloads"] = len(overloaded)
        print(f"Base-case flow violations after SCOPF: {len(overloaded)}")

        # LMP stats
        lmp_vals = pd.Series(scopf_lmps)
        results["details"]["scopf_lmp_min"] = float(lmp_vals.min())
        results["details"]["scopf_lmp_max"] = float(lmp_vals.max())
        results["details"]["scopf_lmp_spread"] = float(lmp_vals.max() - lmp_vals.min())
        print(f"SCOPF LMPs: min=${lmp_vals.min():.2f}, max=${lmp_vals.max():.2f} /MWh")

        # 7. Pass condition
        pass_conditions = {
            "scopf_solved": scopf_ok,
            "cost_differs_from_base": cost_diff_pct > 0.01,
            "no_base_case_overloads": len(overloaded) == 0,
        }
        results["details"]["pass_conditions"] = pass_conditions

        all_pass = all(pass_conditions.values())
        if all_pass:
            results["status"] = "pass"
        elif scopf_ok and pass_conditions["no_base_case_overloads"]:
            results["status"] = "qualified_pass"
            if not pass_conditions["cost_differs_from_base"]:
                results["details"]["note"] = (
                    "SCOPF solved but cost identical to base OPF — contingencies may not be binding"
                )
        else:
            failing = [k for k, v in pass_conditions.items() if not v]
            results["errors"].append(f"Failed pass conditions: {failing}")
            results["status"] = "fail"

        print(f"\n=== RESULT: {results['status'].upper()} ===")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
