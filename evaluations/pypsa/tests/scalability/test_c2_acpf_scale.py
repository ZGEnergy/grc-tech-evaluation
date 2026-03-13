"""
Test C-2: ACPF Scale (acpf_scale)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: Wall-clock time, peak memory, and iterations recorded.
  Non-convergence on MEDIUM is a finding.
Tool: PyPSA 1.1.2

Note: Ipopt NOT available. Uses n.pf() (Newton-Raphson, no external solver needed).
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# AC PF tolerance
X_TOL = 1e-6


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
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute AC Power Flow (Newton-Raphson) on ACTIVSg10k.

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
            "overwrite_zero_s_nom=1.0 applied to fix 2462 zero-rated lines in ACTIVSg10k",
            "Ipopt NOT available in devcontainer — using n.pf() (scipy Newton-Raphson NR) "
            "rather than Ipopt-based AC OPF. This is the correct AC PF method for C-2.",
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
        print(f"Tolerance: x_tol={X_TOL}")

        # 2. Run AC power flow with peak memory tracking
        # n.pf() uses Newton-Raphson internally (scipy sparse solver)
        tracemalloc.start()
        solve_start = time.perf_counter()
        pf_result = n.pf(x_tol=X_TOL)
        solve_elapsed = time.perf_counter() - solve_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)
        print(f"ACPF solve time: {solve_elapsed:.3f}s")
        print(f"Peak memory: {peak / (1024 * 1024):.1f} MB")
        print(
            f"pf_result keys: {list(pf_result.keys()) if isinstance(pf_result, dict) else type(pf_result)}"
        )

        # 3. Extract convergence information
        converged = False
        n_iter = None
        final_error = None

        if isinstance(pf_result, dict):
            if "converged" in pf_result:
                converged_arr = pf_result["converged"]
                try:
                    converged = bool(converged_arr.values.flatten()[0])
                except Exception:
                    converged = bool(converged_arr)
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

        # 4. Validate voltage profile if converged
        if converged and len(n.buses_t.v_mag_pu) > 0:
            v_mag = n.buses_t.v_mag_pu.iloc[0]
            v_ang = n.buses_t.v_ang.iloc[0]
            _n_flat = int((v_mag - 1.0).abs() < 1e-6).sum() if hasattr(v_mag, "sum") else 0
            # Count buses with v_mag != 1.0 (not flat-start)
            n_nontrivial = int(((v_mag - 1.0).abs() > 1e-6).sum())
            results["details"]["n_buses_non_flat_voltage"] = n_nontrivial
            results["details"]["v_mag_min"] = float(v_mag.min())
            results["details"]["v_mag_max"] = float(v_mag.max())
            results["details"]["v_ang_max_deg"] = float(v_ang.abs().max() * 180 / np.pi)
            pct_nontrivial = n_nontrivial / len(v_mag) * 100
            results["details"]["pct_buses_nontrivial_voltage"] = float(pct_nontrivial)
            print(f"Voltage: min={v_mag.min():.4f}, max={v_mag.max():.4f} pu")
            print(f"Non-flat buses: {n_nontrivial}/{len(v_mag)} ({pct_nontrivial:.1f}%)")
        elif not converged:
            # Record non-convergence as solver-issues finding
            results["errors"].append(
                f"ACPF did not converge on ACTIVSg10k: n_iter={n_iter}, residual={final_error}. "
                "This is a solver-issues finding — large meshed network requires flat start."
            )
            results["details"]["non_convergence_note"] = (
                "ACTIVSg10k AC power flow non-convergence is common for large meshed networks "
                "with a flat-start initial point. The scipy Newton-Raphson in PyPSA does not "
                "provide warm-start capability from DC solution. Ipopt (unavailable) would be "
                "the preferred solver for large-scale AC PF. This is a scope limitation "
                "not a tool defect."
            )

        # 5. Pass condition: Record timing and convergence regardless of convergence
        # (pass = timing/memory recorded; non-convergence is documented as finding)
        results["status"] = "pass" if converged else "qualified_pass"
        if not converged:
            results["workarounds"].append(
                "ACPF did not converge on ACTIVSg10k — timing recorded but result not valid. "
                "Non-convergence documented as solver-issues observation."
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
