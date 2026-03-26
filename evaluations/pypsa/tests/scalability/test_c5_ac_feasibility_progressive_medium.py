"""
Test C-5: AC Feasibility — Progressive Relaxation on MEDIUM

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k — 10,000 buses)
Pass condition: Records relaxation level (0%/10%/20%/infeasible). Wall-clock per attempt.
    All outcomes diagnostic.
Tool: PyPSA 1.1.2
Solver: PyPSA internal Newton-Raphson (n.pf())

Methodology: DCPF warm-start, then 0%/10%/20% progressive relaxation.
For AC PF, the shared loader's b=1/x transformer patch should NOT be used since
it is a DC convention. We load raw (without the transformer patch) for AC convergence.
"""

import json
import os
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# Relaxation levels: 0% (original), 10%, 20%
RELAXATION_LEVELS = [0.0, 0.10, 0.20]

# AC PF tolerance
X_TOL = 1e-6


def load_network_for_acpf(network_file: str):
    """Load network WITHOUT the shared loader's DC transformer patch.

    For AC power flow, we need the native transformer model (b = 1/(x*tap)),
    not the DC approximation (b = 1/x).
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


def apply_relaxation(n, relaxation_pct: float):
    """Multiply all branch thermal limits (s_nom) by (1 + relaxation_pct)."""
    factor = 1.0 + relaxation_pct
    if len(n.lines) > 0:
        n.lines["s_nom"] = n.lines["s_nom"] * factor
    if len(n.transformers) > 0:
        n.transformers["s_nom"] = n.transformers["s_nom"] * factor


def attempt_acpf(n, relaxation_pct: float, use_seed: bool, label: str) -> dict:
    """Attempt ACPF at a given relaxation level."""
    result = {
        "relaxation_pct": relaxation_pct,
        "converged": False,
        "wall_clock_seconds": 0.0,
        "peak_memory_mb": 0.0,
        "n_iterations": None,
        "convergence_residual": None,
        "v_mag_min": None,
        "v_mag_max": None,
        "n_buses_nontrivial_voltage": None,
        "pct_buses_nontrivial": None,
        "error": None,
    }

    try:
        n_copy = n.copy()
        if relaxation_pct > 0:
            apply_relaxation(n_copy, relaxation_pct)

        tracemalloc.start()
        solve_start = time.perf_counter()
        pf_result = n_copy.pf(x_tol=X_TOL, use_seed=use_seed)
        solve_elapsed = time.perf_counter() - solve_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result["wall_clock_seconds"] = solve_elapsed
        result["peak_memory_mb"] = peak / (1024 * 1024)

        if isinstance(pf_result, dict):
            if "converged" in pf_result:
                try:
                    result["converged"] = bool(pf_result["converged"].values.flatten()[0])
                except Exception:
                    result["converged"] = bool(pf_result["converged"])
            if "n_iter" in pf_result:
                try:
                    result["n_iterations"] = int(pf_result["n_iter"].values.flatten()[0])
                except Exception:
                    result["n_iterations"] = int(pf_result["n_iter"])
            if "error" in pf_result:
                try:
                    result["convergence_residual"] = float(pf_result["error"].values.flatten()[0])
                except Exception:
                    result["convergence_residual"] = float(pf_result["error"])

        if result["converged"] and len(n_copy.buses_t.v_mag_pu) > 0:
            v_mag = n_copy.buses_t.v_mag_pu.iloc[0]
            n_nontrivial = int(((v_mag - 1.0).abs() > 1e-6).sum())
            result["v_mag_min"] = float(v_mag.min())
            result["v_mag_max"] = float(v_mag.max())
            result["n_buses_nontrivial_voltage"] = n_nontrivial
            result["pct_buses_nontrivial"] = float(n_nontrivial / len(v_mag) * 100)

        print(
            f"  {label}: converged={result['converged']}, "
            f"iter={result['n_iterations']}, "
            f"residual={result['convergence_residual']}, "
            f"time={solve_elapsed:.3f}s, "
            f"mem={result['peak_memory_mb']:.1f} MB"
        )

    except Exception as e:
        try:
            tracemalloc.stop()
        except Exception:
            pass
        result["error"] = f"{type(e).__name__}: {e}"
        print(f"  {label}: ERROR: {e}")

    return result


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute AC Feasibility Progressive Relaxation on MEDIUM.

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
        "workarounds": [
            "Raw import used (without shared loader transformer patch) since "
            "the b=1/x DC patch is not appropriate for AC power flow.",
        ],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        print("=== Loading MEDIUM network ===")
        n = load_network_for_acpf(network_file)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["cpu_threads_available"] = os.cpu_count()
        results["details"]["cpu_threads_used"] = 1
        print(f"  {len(n.buses)} buses, {len(n.lines)} lines, {len(n.generators)} generators")

        # 2. DCPF warm start
        print("\n=== DCPF Warm Start ===")
        dc_start = time.perf_counter()
        n.lpf()
        dc_elapsed = time.perf_counter() - dc_start
        results["details"]["dcpf_seconds"] = dc_elapsed

        if len(n.buses_t.v_ang) > 0:
            n_nonzero = int((n.buses_t.v_ang.iloc[0].abs() > 1e-10).sum())
            print(
                f"  DCPF completed in {dc_elapsed:.3f}s, {n_nonzero}/{len(n.buses)} nonzero angles"
            )
        else:
            print("  DCPF failed to produce angles")

        # 3. Progressive relaxation
        print("\n=== Progressive Relaxation ===")
        relaxation_attempts = []
        first_converged = None

        for relax_pct in RELAXATION_LEVELS:
            label = f"{int(relax_pct * 100)}% relaxation"
            attempt = attempt_acpf(n, relax_pct, use_seed=True, label=label)
            relaxation_attempts.append(attempt)

            if attempt["converged"] and first_converged is None:
                first_converged = f"{int(relax_pct * 100)}%"

        results["details"]["relaxation_attempts"] = relaxation_attempts
        results["details"]["first_converged_relaxation"] = (
            first_converged if first_converged else "infeasible"
        )

        # Use the first converged attempt for headline metrics
        best_attempt = None
        for att in relaxation_attempts:
            if att["converged"]:
                best_attempt = att
                break

        if best_attempt:
            results["details"]["best_solve_seconds"] = best_attempt["wall_clock_seconds"]
            results["details"]["best_peak_memory_mb"] = best_attempt["peak_memory_mb"]
            results["details"]["best_n_iterations"] = best_attempt["n_iterations"]
            results["details"]["best_convergence_residual"] = best_attempt["convergence_residual"]
            results["details"]["best_v_mag_min"] = best_attempt["v_mag_min"]
            results["details"]["best_v_mag_max"] = best_attempt["v_mag_max"]

        # Status: pass = we recorded diagnostic findings (all outcomes informational)
        results["status"] = "pass"

        print("\n=== Summary ===")
        print(f"  First converged at: {results['details']['first_converged_relaxation']}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
