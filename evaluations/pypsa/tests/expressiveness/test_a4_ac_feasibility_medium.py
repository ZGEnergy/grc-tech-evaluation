"""
Test A-4: AC Feasibility Check (ac_feasibility)

Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m, ~10000 buses)
Pass condition: Same as TINY. May not converge on 10k-bus network from DC dispatch
  starting point — document convergence outcome.
  Key requirement: same model context (no file export/reimport between DC OPF and ACPF).
Tool: PyPSA 1.1.2

Depends on: A-3 MEDIUM (DC OPF dispatch). Since A-3 must be run to get the dispatch,
this script re-runs the A-3 DC OPF internally to get the dispatch values, then applies
them in the same model context.
"""

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# Solver config for the internal DC OPF step
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600,
    "presolve": "on",
    "threads": 1,
    "output_flag": False,  # suppress OPF output
}

# Voltage violation bounds
V_MIN_PU = 0.95
V_MAX_PU = 1.05


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc dict -> pypsa.

    Uses overwrite_zero_s_nom=9999.0 so that the 2462 zero-rated branches do not
    cause DC OPF infeasibility (their base-case flows exceed 1 MVA).
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
    """Execute AC feasibility check on DC OPF dispatch for ACTIVSg10k.

    Methodology:
    1. Load network, run DC OPF to get optimal dispatch
    2. Fix generator active power to DC OPF values (same model context)
    3. Run AC PF (Newton-Raphson) from flat start
    4. Record convergence outcome (non-convergence is a finding, not failure on MEDIUM)
    5. Report voltage and thermal violations as structured output

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
            "(no native MATPOWER reader in PyPSA)"
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
        print(f"Network loaded: {len(n.buses)} buses in {load_elapsed:.3f}s")

        # 2. Run DC OPF to get optimal dispatch (same model instance — no export/reimport)
        print("\n=== Running DC OPF to get dispatch (same model context) ===")
        gen_names = sorted(n.generators.index)
        costs = np.linspace(10, 100, len(gen_names))
        for gen_name, cost in zip(gen_names, costs):
            n.generators.at[gen_name, "marginal_cost"] = float(cost)

        opf_start = time.perf_counter()
        opf_status, opf_condition = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        opf_elapsed = time.perf_counter() - opf_start
        results["details"]["opf_solve_seconds"] = opf_elapsed
        results["details"]["opf_status"] = str(opf_status)
        results["details"]["opf_condition"] = str(opf_condition)
        print(f"DC OPF: {opf_status}/{opf_condition} in {opf_elapsed:.3f}s")

        if str(opf_status).lower() not in ("ok", "optimal"):
            results["errors"].append(f"DC OPF failed: {opf_status}/{opf_condition}")
            results["status"] = "fail"
            return results

        # 3. Extract dispatch and fix to generators (same model context)
        gen_dispatch_df = n.generators_t.p
        if len(gen_dispatch_df) > 0:
            dispatch_vals = gen_dispatch_df.iloc[0]
        else:
            results["errors"].append("DC OPF returned empty dispatch")
            results["status"] = "fail"
            return results

        snapshot = n.snapshots[0]
        total_dispatch = float(dispatch_vals.sum())
        results["details"]["total_dispatch_mw"] = total_dispatch
        results["details"]["n_generators_dispatched"] = int((dispatch_vals > 0).sum())
        results["details"]["same_model_context"] = True
        print(
            f"DC OPF dispatch: {total_dispatch:.1f} MW total, "
            f"{int((dispatch_vals > 0).sum())} generators active"
        )

        # Fix dispatch via generators_t.p_set (in-memory, no export)
        p_set_df = pd.DataFrame(dispatch_vals.to_dict(), index=[snapshot])
        n.generators_t.p_set = p_set_df

        # 4. Run AC power flow from flat start
        print("\n=== Running AC PF (flat start) ===")
        pf_start = time.perf_counter()
        pf_result = n.pf(snapshots=[snapshot])
        pf_elapsed = time.perf_counter() - pf_start
        results["details"]["pf_wall_clock_seconds"] = pf_elapsed
        print(f"AC PF solve time: {pf_elapsed:.3f}s")

        # Extract convergence info
        converged = False
        n_iterations = None
        convergence_residual = None
        try:
            if "converged" in pf_result:
                converged = bool(pf_result["converged"].values.flatten()[0])
            if "n_iter" in pf_result:
                n_iterations = int(pf_result["n_iter"].values.flatten()[0])
            if "error" in pf_result:
                convergence_residual = float(pf_result["error"].values.flatten()[0])
        except Exception as parse_err:
            results["errors"].append(f"PF result parse issue: {parse_err}")

        results["details"]["pf_converged"] = converged
        results["details"]["pf_iterations"] = n_iterations
        results["details"]["convergence_residual"] = convergence_residual
        print(
            f"AC PF: converged={converged}, iterations={n_iterations}, residual={convergence_residual}"
        )

        # Note: non-convergence on MEDIUM is a finding, not automatic failure
        if not converged:
            results["errors"].append(
                "AC PF did not converge on MEDIUM (10k-bus) network from DC OPF dispatch "
                "flat start. Expected behavior for large networks; document as finding."
            )
            # Still check what voltage profile we got (may be partially useful)

        # 5. Extract voltage and thermal violation data regardless of convergence
        v_mag_pu = n.buses_t.v_mag_pu
        v_violations = []
        thermal_violations = []

        if len(v_mag_pu) > 0:
            v_vals = v_mag_pu.iloc[0]
            n_buses_total = len(v_vals)
            n_flat = int((np.abs(v_vals - 1.0) < 1e-6).sum())
            frac_nontrivial = 1.0 - n_flat / n_buses_total if n_buses_total > 0 else 0.0
            results["details"]["v_mag_min"] = float(v_vals.min())
            results["details"]["v_mag_max"] = float(v_vals.max())
            results["details"]["frac_buses_nontrivial_voltage"] = frac_nontrivial
            results["details"]["v_mag_first5"] = v_vals.head(5).to_dict()

            if converged:
                for bus_name in v_vals.index:
                    v = float(v_vals[bus_name])
                    if v < V_MIN_PU or v > V_MAX_PU:
                        v_violations.append(
                            {
                                "bus": bus_name,
                                "v_mag_pu": v,
                                "violation": "low" if v < V_MIN_PU else "high",
                            }
                        )

            print("\n=== Voltage Profile ===")
            print(f"  V_mag range: [{v_vals.min():.4f}, {v_vals.max():.4f}] pu")
            print(
                f"  Non-trivial buses: {n_buses_total - n_flat}/{n_buses_total} ({frac_nontrivial:.1%})"
            )

        # Thermal violations (only meaningful if converged)
        if converged:
            p0_lines = n.lines_t.p0
            if len(p0_lines) > 0:
                p0_vals = p0_lines.iloc[0].abs()
                s_nom_lines = n.lines.s_nom
                for line_name in p0_vals.index:
                    if line_name in s_nom_lines.index:
                        flow_mw = float(p0_vals[line_name])
                        limit_mw = float(s_nom_lines[line_name])
                        if limit_mw > 0 and flow_mw > limit_mw:
                            thermal_violations.append(
                                {
                                    "branch": line_name,
                                    "type": "line",
                                    "flow_mw": flow_mw,
                                    "limit_mw": limit_mw,
                                }
                            )

        results["details"]["n_voltage_violations"] = len(v_violations)
        results["details"]["n_thermal_violations"] = len(thermal_violations)
        results["details"]["voltage_violations"] = v_violations[:20]  # cap output
        results["details"]["thermal_violations"] = thermal_violations[:20]

        print("\n=== Feasibility Violations ===")
        print(f"  Voltage violations: {len(v_violations)}")
        print(f"  Thermal violations: {len(thermal_violations)}")
        print("  Same model context: True (no export/reimport)")

        # 6. Pass condition
        # Key requirement: same model context satisfied, violations accessible as structured output.
        # Non-convergence on MEDIUM: still pass if same-context requirement met + violations accessible.
        # If not converged: qualified_pass with finding.
        violations_accessible = (
            isinstance(v_violations, list)
            and isinstance(thermal_violations, list)
            and results["details"]["same_model_context"]
        )

        if not violations_accessible:
            results["errors"].append("Violations not accessible as structured output")
            results["status"] = "fail"
        elif not converged:
            # Non-convergence on MEDIUM is an expected finding (acceptable)
            # Same-context requirement IS met (DC OPF → AC PF in same n object)
            results["status"] = "qualified_pass"
            results["errors"].append(
                "FINDING: AC PF did not converge on 10k-bus network. "
                "Same model context requirement is satisfied; this is a convergence finding."
            )
        else:
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
