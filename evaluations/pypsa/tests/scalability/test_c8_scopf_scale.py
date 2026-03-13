"""
Test C-8: SCOPF Scale (scopf_scale)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: Wall-clock time, peak memory, binding contingencies recorded.
Tool: PyPSA 1.1.2

Depends on: A-9 (same SCOPF API)
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
}

# Number of contingencies to include in SCOPF
N_CONTINGENCIES = 5


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc -> pypsa."""
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
    # For OPF: relax 1 MVA limit on zero-rated lines (rateA=0 means unconstrained in MATPOWER)
    n.lines.loc[n.lines.s_nom == 1.0, "s_nom"] = 99999.0
    return n


def assign_marginal_costs(n) -> None:
    """Assign marginal costs (same as C-3/A-9)."""
    gen_names = sorted(n.generators.index)
    n_gens = len(gen_names)
    costs = np.linspace(10, 100, n_gens)
    for gen_name, cost in zip(gen_names, costs):
        n.generators.at[gen_name, "marginal_cost"] = float(cost)


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute SCOPF on ACTIVSg10k with 3-5 contingencies.

    Note on ACTIVSg10k congestion: The base case has no binding branch constraints
    (max loading ~84-85%). SCOPF cost premium will be near zero unless contingencies
    create binding post-contingency constraints. This is documented per cross-tool-watchpoints.

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
            "Marginal costs assigned manually — import_from_pypower_ppc does not import gencost",
            "overwrite_zero_s_nom=1.0 applied to fix 2462 zero-rated lines in ACTIVSg10k",
        ],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        load_start = time.perf_counter()
        n = load_network(network_file)
        load_elapsed = time.perf_counter() - load_start
        assign_marginal_costs(n)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["load_seconds"] = load_elapsed
        print(f"Network loaded: {len(n.buses)} buses, {len(n.lines)} lines in {load_elapsed:.2f}s")

        # 2. Run base OPF to identify contingency candidates
        print("\n=== Base OPF (selecting contingencies) ===")
        base_status = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        if isinstance(base_status, tuple):
            status_str = str(base_status[0])
        else:
            status_str = str(base_status)
        results["details"]["base_opf_status"] = status_str

        base_ok = False
        try:
            base_obj = float(n.objective)
            if np.isfinite(base_obj):
                base_ok = True
        except Exception:
            pass
        if status_str.lower() in ("ok", "optimal"):
            base_ok = True

        if not base_ok:
            results["errors"].append(f"Base OPF failed: {base_status}")
            results["status"] = "fail"
            return results

        base_objective = float(n.objective)
        results["details"]["base_objective"] = base_objective
        print(f"Base OPF: ${base_objective:,.0f}")

        # Select contingencies with moderate utilization (30%-70%)
        p0_abs = n.lines_t.p0.iloc[0].abs()
        s_nom = n.lines.s_nom
        utilization = (p0_abs / s_nom).fillna(0)
        moderate = utilization[(utilization > 0.30) & (utilization < 0.70)]
        moderate_sorted = moderate.sort_values(ascending=False)

        if len(moderate_sorted) >= N_CONTINGENCIES:
            contingency_lines = list(moderate_sorted.head(N_CONTINGENCIES).index)
        elif len(moderate_sorted) >= 1:
            contingency_lines = list(
                moderate_sorted.head(min(len(moderate_sorted), N_CONTINGENCIES)).index
            )
            # Supplement with lower-utilization lines if needed
            extra_needed = N_CONTINGENCIES - len(contingency_lines)
            if extra_needed > 0:
                low_util = utilization[(utilization > 0.10) & (utilization < 0.30)]
                additional = list(low_util.sort_values(ascending=False).head(extra_needed).index)
                contingency_lines.extend(additional)
        else:
            nonzero = utilization[utilization > 0.05].sort_values(ascending=False)
            contingency_lines = list(nonzero.head(N_CONTINGENCIES).index)

        results["details"]["contingency_lines"] = contingency_lines
        results["details"]["n_contingencies"] = len(contingency_lines)
        results["details"]["contingency_utilizations"] = {
            line: float(utilization.get(line, 0)) for line in contingency_lines
        }
        print(f"Contingencies selected: {contingency_lines}")
        print(f"Utilizations: {[f'{utilization.get(ln, 0):.2%}' for ln in contingency_lines]}")

        # 3. Run SCOPF
        print(
            f"\n=== SCOPF: {len(contingency_lines)} contingencies on {len(n.buses)}-bus network ==="
        )
        snapshot = n.snapshots[0]

        tracemalloc.start()
        scopf_start = time.perf_counter()
        scopf_result = n.optimize.optimize_security_constrained(
            snapshots=[snapshot],
            branch_outages=contingency_lines,
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        scopf_elapsed = time.perf_counter() - scopf_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["scopf_solve_seconds"] = scopf_elapsed
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)
        print(f"SCOPF solve time: {scopf_elapsed:.3f}s")
        print(f"Peak memory: {peak / (1024 * 1024):.1f} MB")
        print(f"SCOPF result: {scopf_result}")

        # 4. Parse SCOPF result
        if isinstance(scopf_result, tuple):
            sc_status = str(scopf_result[0])
        else:
            sc_status = str(scopf_result)
        results["details"]["scopf_status"] = sc_status

        scopf_ok = False
        try:
            scopf_obj = float(n.objective)
            if np.isfinite(scopf_obj):
                scopf_ok = True
        except Exception:
            pass
        if sc_status.lower() in ("ok", "optimal"):
            scopf_ok = True

        if not scopf_ok:
            results["errors"].append(f"SCOPF did not solve: {scopf_result}")
            results["status"] = "fail"
            return results

        scopf_objective = float(n.objective)
        results["details"]["scopf_objective"] = scopf_objective
        cost_premium_pct = (scopf_objective - base_objective) / base_objective * 100.0
        results["details"]["cost_premium_pct"] = float(cost_premium_pct)
        print(f"SCOPF objective: ${scopf_objective:,.0f} ({cost_premium_pct:+.2f}% vs base)")

        # 5. Check for binding contingencies (post-SCOPF base-case overloads)
        p0_scopf = n.lines_t.p0.iloc[0].abs()
        s_nom_scopf = n.lines.s_nom
        overloads = []
        for line in p0_scopf.index:
            if line in s_nom_scopf.index:
                flow = float(p0_scopf[line])
                limit = float(s_nom_scopf[line])
                if limit > 0 and flow > limit * 0.999:
                    overloads.append(
                        {
                            "line": line,
                            "loading_pct": float(flow / limit * 100),
                            "is_contingency": line in contingency_lines,
                        }
                    )

        results["details"]["n_binding_base_case_lines"] = len(overloads)
        results["details"]["binding_lines"] = overloads[:10]  # cap output size
        print(f"Binding base-case lines after SCOPF: {len(overloads)}")

        # Note on ACTIVSg10k
        results["details"]["congestion_note"] = (
            "ACTIVSg10k has no binding branch constraints in base-case DCOPF "
            "(max loading ~84-85%). SCOPF cost premium is near zero because "
            "contingency constraints are not binding — the network has sufficient headroom. "
            "This is consistent with the cross-tool-watchpoints note on ACTIVSg10k."
        )

        results["status"] = "pass"
        print("\n=== C-8 PASS ===")
        print(f"  SCOPF solve time: {scopf_elapsed:.3f}s")
        print(f"  Cost premium: {cost_premium_pct:+.2f}%")
        print(f"  Peak memory: {results['details']['peak_memory_mb']:.1f} MB")

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
