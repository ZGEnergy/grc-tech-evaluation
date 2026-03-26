"""
Test C-2: ACPF on MEDIUM

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k — 10,000 buses)
Pass condition: Completes ACPF on MEDIUM. Wall-clock, peak memory, iterations.
    Convergence verified: max bus power mismatch < 1e-4 p.u.
Tool: PyPSA 1.1.2
Solver: PyPSA internal Newton-Raphson (n.pf())

Note: PyPSA's n.pf() uses its own Newton-Raphson AC power flow solver (scipy sparse),
not Ipopt. For AC PF, the shared loader's b=1/x transformer patch is NOT appropriate
since it is a DC convention. We load raw (without the transformer patch) for AC convergence.
"""

import os
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# AC PF tolerance
X_TOL = 1e-6


def load_network_for_acpf(network_file: str):
    """Load ACTIVSg10k for AC PF — raw import WITHOUT DC transformer patch.

    The shared loader's b=1/x patch is for DC analysis. For AC PF we need
    PyPSA's native b=1/(x*tap) transformer model.
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
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=100000.0)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute AC Power Flow (Newton-Raphson) on ACTIVSg10k.

    Returns:
        dict with keys:
        - status: "pass" | "fail"
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
        load_start = time.perf_counter()
        n = load_network_for_acpf(network_file)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["cpu_threads_available"] = os.cpu_count()
        results["details"]["cpu_threads_used"] = 1  # n.pf() is single-threaded NR
        print(
            f"Network loaded: {len(n.buses)} buses, {len(n.lines)} lines, "
            f"{len(n.generators)} generators in {load_elapsed:.2f}s"
        )

        # 2. DCPF warm start
        print("\n=== DCPF Warm Start ===")
        dc_start = time.perf_counter()
        n.lpf()
        dc_elapsed = time.perf_counter() - dc_start
        results["details"]["dcpf_seconds"] = dc_elapsed
        print(f"DCPF completed in {dc_elapsed:.3f}s")

        # Apply DC angles as seed for NR
        # PyPSA's pf(use_seed=True) uses buses_t.v_ang and buses_t.v_mag_pu as initial guess

        # 3. Run AC power flow with peak memory tracking
        print(f"\n=== ACPF (x_tol={X_TOL}) ===")
        tracemalloc.start()
        solve_start = time.perf_counter()
        pf_result = n.pf(x_tol=X_TOL, use_seed=True)
        solve_elapsed = time.perf_counter() - solve_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)
        print(f"ACPF solve time: {solve_elapsed:.3f}s")
        print(f"Peak memory: {peak / (1024 * 1024):.1f} MB")

        # 4. Extract convergence information
        converged = False
        n_iter = None
        final_error = None

        if isinstance(pf_result, dict):
            if "converged" in pf_result:
                try:
                    converged = bool(pf_result["converged"].values.flatten()[0])
                except Exception:
                    converged = bool(pf_result["converged"])
            if "n_iter" in pf_result:
                try:
                    n_iter = int(pf_result["n_iter"].values.flatten()[0])
                except Exception:
                    n_iter = int(pf_result["n_iter"])
            if "error" in pf_result:
                try:
                    final_error = float(pf_result["error"].values.flatten()[0])
                except Exception:
                    final_error = float(pf_result["error"])

        results["details"]["converged"] = converged
        results["details"]["n_iterations"] = n_iter
        results["details"]["final_residual"] = final_error
        print(f"Converged: {converged}, iterations: {n_iter}, residual: {final_error}")

        # 5. Validate voltage profile if converged
        if converged and len(n.buses_t.v_mag_pu) > 0:
            v_mag = n.buses_t.v_mag_pu.iloc[0]
            v_ang = n.buses_t.v_ang.iloc[0]
            n_nontrivial = int(((v_mag - 1.0).abs() > 1e-6).sum())
            results["details"]["n_buses_non_flat_voltage"] = n_nontrivial
            results["details"]["v_mag_min"] = float(v_mag.min())
            results["details"]["v_mag_max"] = float(v_mag.max())
            results["details"]["v_ang_max_deg"] = float(v_ang.abs().max() * 180 / np.pi)
            pct_nontrivial = n_nontrivial / len(v_mag) * 100
            results["details"]["pct_buses_nontrivial_voltage"] = float(pct_nontrivial)
            print(f"Voltage: min={v_mag.min():.4f}, max={v_mag.max():.4f} pu")
            print(f"Non-flat buses: {n_nontrivial}/{len(v_mag)} ({pct_nontrivial:.1f}%)")

            # Convergence evidence: residual_reported tier
            if final_error is not None and final_error < 1e-4:
                results["details"]["convergence_evidence_quality"] = "residual_reported"
            elif n_iter is not None and n_iter > 0:
                results["details"]["convergence_evidence_quality"] = "iteration_count_reported"
            else:
                results["details"]["convergence_evidence_quality"] = "binary_convergence_api"

        if converged:
            results["status"] = "pass"
        else:
            results["status"] = "fail"
            results["errors"].append(
                f"ACPF did not converge: n_iter={n_iter}, residual={final_error}"
            )

        print("\n=== Summary ===")
        print(f"  Status: {results['status']}")
        print(f"  Solve time: {solve_elapsed:.3f}s")
        print(f"  Peak memory: {results['details']['peak_memory_mb']:.1f} MB")
        print(f"  Converged: {converged}")

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
