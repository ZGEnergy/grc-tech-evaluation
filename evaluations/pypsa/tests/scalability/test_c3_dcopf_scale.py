"""
Test C-3: DC OPF Scale (dcopf_scale)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: Wall-clock time, peak memory, objective value recorded.
Tool: PyPSA 1.1.2

Note: Config says "HiGHS, GLPK" but GLPK is not available — document HiGHS only.
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# Solver configuration
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
    "log_to_console": True,
}


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc -> pypsa.

    For OPF: zero-rated branches are set to a large value (99999 MVA) so they
    don't create infeasibility. Using overwrite_zero_s_nom=1.0 restricts those
    branches to 1 MVA which blocks OPF solutions when ~25% of lines are zero-rated.
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
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=1.0)
    # For OPF: relax the 1 MVA limit on zero-rated lines to 99999 MVA
    # (zero-rated in MATPOWER means "no thermal limit" — not "blocked")
    n.lines.loc[n.lines.s_nom == 1.0, "s_nom"] = 99999.0
    return n


def assign_marginal_costs(n) -> None:
    """Assign marginal costs to generators (not in pypower ppc gencost).

    Uses a simple linear scale from $10 to $100/MWh across the generator fleet.
    This creates a merit-order dispatch incentive.
    """
    gen_names = sorted(n.generators.index)
    n_gens = len(gen_names)
    costs = np.linspace(10, 100, n_gens)
    for gen_name, cost in zip(gen_names, costs):
        n.generators.at[gen_name, "marginal_cost"] = float(cost)


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DC OPF on ACTIVSg10k with HiGHS.

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
            "Used matpowercaseframes.CaseFrames to parse .m -> pypower ppc -> pypsa "
            "(no native MATPOWER reader in PyPSA)",
            "Zero-rated lines (2462 of 9726) set to 99999 MVA for OPF — MATPOWER rateA=0 means "
            "'no thermal limit', but overwrite_zero_s_nom=1.0 creates artificial 1 MVA bottlenecks "
            "making OPF infeasible. Setting to 99999 MVA restores intended 'unconstrained' semantics.",
            "Marginal costs assigned manually (import_from_pypower_ppc does not import gencost): "
            "linear $10–$100/MWh across 2485 generators sorted by name",
            "GLPK not available in devcontainer — HiGHS only (GLPK was requested in config)",
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
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["load_seconds"] = load_elapsed
        print(
            f"Network loaded: {len(n.buses)} buses, {len(n.lines)} lines, "
            f"{len(n.generators)} generators in {load_elapsed:.2f}s"
        )

        # 2. Assign marginal costs
        assign_marginal_costs(n)
        results["details"]["marginal_cost_range"] = {
            "min": float(n.generators.marginal_cost.min()),
            "max": float(n.generators.marginal_cost.max()),
        }
        print(
            f"Marginal costs: ${n.generators.marginal_cost.min():.1f}–"
            f"${n.generators.marginal_cost.max():.1f}/MWh"
        )

        # 3. Run DC OPF with HiGHS and peak memory tracking
        tracemalloc.start()
        solve_start = time.perf_counter()
        opt_result = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        solve_elapsed = time.perf_counter() - solve_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)
        print(f"DC OPF solve time: {solve_elapsed:.3f}s")
        print(f"Peak memory: {peak / (1024 * 1024):.1f} MB")
        print(f"Solver result: {opt_result}")

        # 4. Parse result status
        if isinstance(opt_result, tuple):
            status_str, condition_str = str(opt_result[0]), str(opt_result[1])
        else:
            status_str = str(opt_result)
            condition_str = ""
        results["details"]["solver_status"] = status_str
        results["details"]["solver_condition"] = condition_str

        solve_ok = status_str.lower() in ("ok", "optimal")
        if not solve_ok:
            # Try checking if objective is finite
            try:
                obj = float(n.objective)
                if np.isfinite(obj):
                    solve_ok = True
            except Exception:
                pass

        if not solve_ok:
            results["errors"].append(f"DC OPF did not solve: {opt_result}")
            results["status"] = "fail"
            results["details"]["solve_failed"] = True
            return results

        # 5. Extract results
        objective = float(n.objective)
        results["details"]["objective_dollar"] = objective
        print(f"Objective: ${objective:,.0f}")

        # Generator dispatch stats
        if len(n.generators_t.p) > 0:
            dispatch = n.generators_t.p.iloc[0]
            results["details"]["dispatch_min_mw"] = float(dispatch.min())
            results["details"]["dispatch_max_mw"] = float(dispatch.max())
            results["details"]["dispatch_total_mw"] = float(dispatch.sum())
            results["details"]["n_generators_dispatched"] = int((dispatch > 0.1).sum())
            print(f"Dispatch: total={dispatch.sum():.0f} MW, max={dispatch.max():.0f} MW")

        # LMP stats
        if len(n.buses_t.marginal_price) > 0:
            lmps = n.buses_t.marginal_price.iloc[0]
            results["details"]["lmp_min"] = float(lmps.min())
            results["details"]["lmp_max"] = float(lmps.max())
            results["details"]["lmp_mean"] = float(lmps.mean())
            results["details"]["lmp_uniform"] = bool(lmps.max() - lmps.min() < 0.01)
            print(
                f"LMPs: min=${lmps.min():.2f}, max=${lmps.max():.2f}, mean=${lmps.mean():.2f}/MWh"
            )
            if lmps.max() - lmps.min() < 0.01:
                print("  NOTE: LMPs are uniform — ACTIVSg10k is uncongested in base case")
                results["details"]["congestion_note"] = (
                    "LMPs are uniform across all 10,000 buses — ACTIVSg10k has no binding "
                    "branch constraints in base-case DCOPF (max loading ~84-85%). "
                    "This is consistent with the cross-tool watchpoints note."
                )

        # Branch loading stats
        if len(n.lines_t.p0) > 0:
            flows = n.lines_t.p0.iloc[0].abs()
            s_nom = n.lines.s_nom
            utilization = flows / s_nom
            n_binding = int((utilization >= 0.999).sum())
            results["details"]["max_line_loading_pct"] = float(utilization.max() * 100)
            results["details"]["n_binding_lines"] = n_binding
            print(f"Line loading: max={utilization.max() * 100:.1f}%, binding={n_binding}")

        results["details"]["solver_used"] = SOLVER_NAME
        results["details"]["glpk_available"] = False
        results["details"]["glpk_note"] = "GLPK not installed in devcontainer; HiGHS only"

        results["status"] = "pass"
        print("\n=== C-3 PASS: DC OPF on 10k bus network ===")
        print(
            f"  Solve time: {solve_elapsed:.3f}s, Peak memory: {results['details']['peak_memory_mb']:.1f} MB"
        )
        print(f"  Objective: ${objective:,.0f}")

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
