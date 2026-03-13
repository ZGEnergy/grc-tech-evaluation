"""
Test B-7: AC Feasibility Extension Assessment (ac_feasibility_extension)

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: DC OPF solves on 10k-bus. AC PF attempted with DC-warm-start dispatch.
  Record timing for both DC OPF and AC PF. Document convergence behavior.
  (B-7 at MEDIUM is a timing/scale assessment of the DC OPF → AC PF workflow.)
Tool: PyPSA 1.1.2
"""

import time
import traceback
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
    "output_flag": False,
}


def load_network(network_file: str):
    """Load ACTIVSg10k with differentiated marginal costs."""
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
    # overwrite_zero_s_nom=100000 gives unconstrained lines a high (100 GVA) thermal limit
    # so OPF doesn't fail on lines with zero/missing ratings in ACTIVSg10k
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=100000.0)

    # Assign differentiated marginal costs ($10–$100/MWh)
    gen_names = sorted(n.generators.index)
    n_gens = len(gen_names)
    costs = np.linspace(10, 100, n_gens)
    for gen_name, cost in zip(gen_names, costs):
        n.generators.at[gen_name, "marginal_cost"] = float(cost)

    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DC OPF then AC PF feasibility check on 10k-bus network.

    Step 1: DC OPF — record solve time and objective.
    Step 2: Apply DC OPF dispatch to AC PF — record AC PF time and convergence.

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
        import pandas as pd

        # 1. Load network
        print("Loading 10k network...")
        n = load_network(network_file)
        n_buses = len(n.buses)
        n_gens = len(n.generators)
        n_lines = len(n.lines)
        print(f"Loaded: {n_buses} buses, {n_gens} generators, {n_lines} lines")

        results["details"]["n_buses"] = n_buses
        results["details"]["n_generators"] = n_gens
        results["details"]["n_lines"] = n_lines
        results["details"]["base_mva"] = float(
            n.meta.get("baseMVA", 100.0) if hasattr(n, "meta") else 100.0
        )

        # 2. Run DC OPF
        print("Running DC OPF...")
        t_opf_start = time.perf_counter()
        status_opf, cond_opf = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        t_opf_elapsed = time.perf_counter() - t_opf_start
        print(f"DC OPF done in {t_opf_elapsed:.2f}s: {status_opf}, {cond_opf}")

        results["details"]["dcopf_status"] = str(status_opf)
        results["details"]["dcopf_condition"] = str(cond_opf)
        results["details"]["dcopf_seconds"] = t_opf_elapsed

        if str(status_opf).lower() not in ("ok", "optimal"):
            results["errors"].append(f"DC OPF failed: {status_opf}, {cond_opf}")
            results["status"] = "fail"
            return results

        obj_opf = float(n.objective)
        results["details"]["dcopf_objective"] = obj_opf
        print(f"DC OPF objective: ${obj_opf:,.2f}/h")

        # Extract dispatch from DC OPF result
        dispatch = n.generators_t.p.iloc[0].copy()
        dispatch_total = float(dispatch.sum())
        dispatch_max = float(dispatch.max())
        dispatch_min = float(dispatch.min())
        print(
            f"DC dispatch: total={dispatch_total:.2f} MW, max={dispatch_max:.2f}, min={dispatch_min:.2f}"
        )

        results["details"]["dcopf_dispatch_total_mw"] = dispatch_total
        results["details"]["dcopf_dispatch_max_mw"] = dispatch_max
        results["details"]["dcopf_dispatch_min_mw"] = dispatch_min

        # 3. Apply DC dispatch to AC PF via in-memory assignment
        # Load fresh network for AC PF (to avoid linopy model state)
        print("Loading fresh network for AC PF...")
        n_ac = load_network(network_file)
        snapshot = n_ac.snapshots[0]

        # Apply DC OPF dispatch
        n_ac.generators_t.p_set = pd.DataFrame(
            {g: [float(dispatch.get(g, 0.0))] for g in n_ac.generators.index},
            index=[snapshot],
        )

        # 4. Run AC PF with DC warm start
        print("Running AC PF (Newton-Raphson)...")
        t_acpf_start = time.perf_counter()
        try:
            pf_result = n_ac.pf(snapshots=[snapshot])
            t_acpf_elapsed = time.perf_counter() - t_acpf_start
            print(f"AC PF done in {t_acpf_elapsed:.2f}s")

            # Parse convergence result
            converged = None
            n_iter = None
            residual = None
            try:
                conv_val = pf_result.get("converged") if isinstance(pf_result, dict) else None
                if conv_val is None and hasattr(pf_result, "__getitem__"):
                    try:
                        conv_val = pf_result["converged"]
                    except (KeyError, TypeError):
                        pass
                if conv_val is not None:
                    converged = bool(
                        conv_val.values.flatten()[0] if hasattr(conv_val, "values") else conv_val
                    )
                iter_val = pf_result.get("n_iter") if isinstance(pf_result, dict) else None
                if iter_val is None and hasattr(pf_result, "__getitem__"):
                    try:
                        iter_val = pf_result["n_iter"]
                    except (KeyError, TypeError):
                        pass
                if iter_val is not None:
                    n_iter = int(
                        iter_val.values.flatten()[0] if hasattr(iter_val, "values") else iter_val
                    )
                err_val = pf_result.get("error") if isinstance(pf_result, dict) else None
                if err_val is None and hasattr(pf_result, "__getitem__"):
                    try:
                        err_val = pf_result["error"]
                    except (KeyError, TypeError):
                        pass
                if err_val is not None:
                    residual = float(
                        err_val.values.flatten()[0] if hasattr(err_val, "values") else err_val
                    )
            except Exception as parse_err:
                print(f"Warning: could not parse pf_result: {parse_err}")

            print(f"AC PF converged: {converged}, n_iter: {n_iter}, residual: {residual}")

            # Voltage magnitudes
            v_mag = n_ac.buses_t.v_mag_pu.iloc[0] if len(n_ac.buses_t.v_mag_pu) > 0 else None
            if v_mag is not None:
                v_min = float(v_mag.min())
                v_max = float(v_mag.max())
                n_viol_low = int((v_mag < 0.95).sum())
                n_viol_high = int((v_mag > 1.05).sum())
                n_flat_start = int((np.abs(v_mag - 1.0) < 1e-6).sum())
                print(
                    f"Voltage magnitudes: min={v_min:.4f}, max={v_max:.4f}, "
                    f"violations=[{n_viol_low} low, {n_viol_high} high], "
                    f"flat-start buses: {n_flat_start}"
                )
            else:
                v_min = v_max = n_viol_low = n_viol_high = n_flat_start = None

            results["details"]["acpf_seconds"] = t_acpf_elapsed
            results["details"]["acpf_converged"] = converged
            results["details"]["acpf_iterations"] = n_iter
            results["details"]["acpf_residual"] = residual
            results["details"]["acpf_v_mag_min"] = v_min
            results["details"]["acpf_v_mag_max"] = v_max
            results["details"]["acpf_n_voltage_violations_low"] = n_viol_low
            results["details"]["acpf_n_voltage_violations_high"] = n_viol_high
            results["details"]["acpf_n_flat_start_buses"] = n_flat_start

            acpf_passed = converged is True
            results["details"]["acpf_pass"] = acpf_passed

        except Exception as acpf_err:
            t_acpf_elapsed = time.perf_counter() - t_acpf_start
            acpf_error_msg = f"{type(acpf_err).__name__}: {acpf_err}"
            print(f"AC PF raised exception: {acpf_error_msg}")
            results["details"]["acpf_error"] = acpf_error_msg
            results["details"]["acpf_seconds"] = t_acpf_elapsed
            results["details"]["acpf_converged"] = False
            acpf_passed = False

        # 5. Pass condition: DC OPF succeeded; AC PF attempted.
        # At MEDIUM scale (10k buses), AC PF convergence is not guaranteed
        # (cross-tool watchpoints: 10k network may have AC convergence difficulty).
        # Pass = DC OPF succeeded + AC PF attempted (even if non-convergent).
        errors = []
        if str(status_opf).lower() not in ("ok", "optimal"):
            errors.append(f"DC OPF failed: {status_opf}")

        # AC PF is a best-effort — document result but don't fail on AC non-convergence
        # at MEDIUM scale per B-7 assessment nature
        results["errors"].extend(errors)

        if not errors:
            if acpf_passed:
                results["status"] = "pass"
            else:
                # DC OPF passed, AC PF attempted but non-convergent at 10k scale
                results["status"] = "qualified_pass"
                results["workarounds"].append(
                    "AC PF did not converge on 10k-bus network with flat start. "
                    "DC OPF → AC PF workflow is architecturally valid but AC convergence "
                    "on large networks depends on initial point quality and reactive power modeling."
                )
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
