"""
Test C-5: AC Feasibility — Progressive Relaxation on SMALL and MEDIUM

Dimension: scalability
Network: SMALL (ACTIVSg2000) / MEDIUM (ACTIVSg10k)
Pass condition: Records relaxation level required (0%, 10%, 20%, or infeasible).
    Wall-clock time per attempt. Whether solution was found. All outcomes are
    diagnostic findings.
Tool: PyPSA 1.1.2
Solver: Ipopt (via n.pf() Newton-Raphson — PyPSA uses internal NR, not Ipopt)

Note: PyPSA's n.pf() uses its own Newton-Raphson AC power flow solver (scipy sparse),
not Ipopt. Ipopt is for NLP optimization, not power flow. We use n.pf() as the AC PF
method, which is the correct approach for PyPSA.

For AC PF, the shared loader's b=1/x transformer patch should NOT be used since it
is a DC convention. We load raw (without the transformer patch) for AC convergence.
"""

import json
import time
import traceback
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

DEFAULT_NETWORK_SMALL = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m")
DEFAULT_NETWORK_MEDIUM = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# Relaxation levels: 0% (original), 10%, 20%
RELAXATION_LEVELS = [0.0, 0.10, 0.20]

# AC PF tolerance
X_TOL = 1e-6

# Timeout per attempt (seconds)
TIMEOUT_SECONDS = 1800  # 30 minutes


def load_network_raw(network_file: str):
    """Load network WITHOUT the shared loader's DC transformer patch.

    For AC power flow, we need the native transformer model (b = 1/(x*tap)),
    not the DC approximation (b = 1/x). So we load directly via
    matpowercaseframes without the shared loader's patch.
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


def run_dcpf_warmstart(n):
    """Run DCPF to get warm-start voltage angles.

    Returns dict with angle values per bus, or None if DCPF fails.
    """
    n.lpf()
    if len(n.buses_t.v_ang) > 0:
        angles = n.buses_t.v_ang.iloc[0].to_dict()
        return angles
    return None


def apply_dc_warmstart(n, dc_angles: dict):
    """Apply DC solution angles as initial guess for AC PF.

    PyPSA's n.pf(use_seed=True) uses the current v_mag_pu and v_ang
    values in buses_t as the initial point.
    """
    import pandas as pd

    snapshot = n.snapshots[0]

    # Set voltage angles from DC solution
    for bus_name, angle in dc_angles.items():
        if bus_name in n.buses.index:
            if "v_ang" not in n.buses_t or len(n.buses_t.v_ang) == 0:
                n.buses_t.v_ang = pd.DataFrame(0.0, index=n.snapshots, columns=n.buses.index)
            n.buses_t.v_ang.at[snapshot, bus_name] = angle

    # Keep voltage magnitudes at 1.0 pu (DCPF doesn't produce v_mag)
    if "v_mag_pu" not in n.buses_t or len(n.buses_t.v_mag_pu) == 0:
        n.buses_t.v_mag_pu = pd.DataFrame(1.0, index=n.snapshots, columns=n.buses.index)


def apply_relaxation(n, relaxation_pct: float):
    """Multiply all branch thermal limits (s_nom) by (1 + relaxation_pct).

    E.g., relaxation_pct=0.10 means 10% relaxation: s_nom *= 1.10
    """
    factor = 1.0 + relaxation_pct
    if len(n.lines) > 0:
        n.lines["s_nom"] = n.lines["s_nom"] * factor
    if len(n.transformers) > 0:
        n.transformers["s_nom"] = n.transformers["s_nom"] * factor


def attempt_acpf(n, relaxation_pct: float, dc_angles: dict | None, label: str) -> dict:
    """Attempt ACPF at a given relaxation level with DC warm start.

    Returns a dict with convergence results.
    """
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
        # Apply relaxation to a fresh copy
        n_copy = n.copy()
        if relaxation_pct > 0:
            apply_relaxation(n_copy, relaxation_pct)

        # Apply DC warm start if available
        if dc_angles is not None:
            apply_dc_warmstart(n_copy, dc_angles)
            use_seed = True
        else:
            use_seed = False

        # Run AC PF
        tracemalloc.start()
        solve_start = time.perf_counter()
        pf_result = n_copy.pf(x_tol=X_TOL, use_seed=use_seed)
        solve_elapsed = time.perf_counter() - solve_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result["wall_clock_seconds"] = solve_elapsed
        result["peak_memory_mb"] = peak / (1024 * 1024)

        # Extract convergence info
        if isinstance(pf_result, dict):
            if "converged" in pf_result:
                try:
                    converged_arr = pf_result["converged"]
                    result["converged"] = bool(converged_arr.values.flatten()[0])
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

        # Validate voltage profile if converged
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


def run_progressive_relaxation(network_file: str, tier_label: str) -> dict:
    """Run progressive relaxation on a single network.

    1. DCPF for warm-start angles
    2. ACPF at 0% relaxation
    3. ACPF at 10% relaxation
    4. ACPF at 20% relaxation
    """
    tier_result = {
        "tier": tier_label,
        "network_file": network_file,
        "n_buses": 0,
        "n_lines": 0,
        "n_generators": 0,
        "dcpf_warm_start": False,
        "dcpf_seconds": 0.0,
        "relaxation_attempts": [],
        "first_converged_relaxation": None,
        "error": None,
    }

    try:
        # Load network
        print(f"\n=== {tier_label}: Loading network ===")
        n = load_network_raw(network_file)
        tier_result["n_buses"] = len(n.buses)
        tier_result["n_lines"] = len(n.lines)
        tier_result["n_generators"] = len(n.generators)
        print(f"  {len(n.buses)} buses, {len(n.lines)} lines, {len(n.generators)} generators")

        # Run DCPF for warm start
        print(f"\n=== {tier_label}: DCPF warm start ===")
        dc_start = time.perf_counter()
        dc_angles = run_dcpf_warmstart(n)
        dc_elapsed = time.perf_counter() - dc_start
        tier_result["dcpf_seconds"] = dc_elapsed
        tier_result["dcpf_warm_start"] = dc_angles is not None
        if dc_angles:
            n_nonzero = sum(1 for v in dc_angles.values() if abs(v) > 1e-10)
            print(
                f"  DCPF completed in {dc_elapsed:.3f}s, "
                f"{n_nonzero}/{len(dc_angles)} buses with nonzero angles"
            )
        else:
            print("  DCPF failed to produce angles")

        # Progressive relaxation attempts
        print(f"\n=== {tier_label}: Progressive Relaxation ===")
        for relax_pct in RELAXATION_LEVELS:
            label = f"{int(relax_pct * 100)}% relaxation"
            attempt = attempt_acpf(n, relax_pct, dc_angles, label)
            tier_result["relaxation_attempts"].append(attempt)

            if attempt["converged"] and tier_result["first_converged_relaxation"] is None:
                tier_result["first_converged_relaxation"] = f"{int(relax_pct * 100)}%"

        if tier_result["first_converged_relaxation"] is None:
            tier_result["first_converged_relaxation"] = "infeasible (all attempts failed)"

    except Exception as e:
        tier_result["error"] = f"{type(e).__name__}: {e}"
        print(f"ERROR: {e}")

    return tier_result


def run(
    network_file: str = DEFAULT_NETWORK_SMALL,
    timeseries_dir: str | None = None,
    run_medium: bool = False,
) -> dict:
    """Execute AC Feasibility Progressive Relaxation.

    By default runs SMALL only. Set run_medium=True to also run MEDIUM.

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
            "PyPSA uses internal Newton-Raphson for AC PF (n.pf()), not Ipopt. "
            "Ipopt is an NLP optimizer, not a power flow solver. PyPSA's NR solver "
            "is the correct AC PF method for this tool.",
            "Raw import used (without shared loader transformer patch) since "
            "the b=1/x DC patch breaks AC convergence.",
        ],
    }

    start = time.perf_counter()
    try:
        # Run SMALL
        small_result = run_progressive_relaxation(network_file, "SMALL")
        results["details"]["SMALL"] = small_result

        # Run MEDIUM if requested
        if run_medium:
            medium_result = run_progressive_relaxation(DEFAULT_NETWORK_MEDIUM, "MEDIUM")
            results["details"]["MEDIUM"] = medium_result

        # Status: pass means we recorded the diagnostic findings
        # (all outcomes are informational per the pass condition)
        results["status"] = "pass"

        print("\n=== C-5 Summary ===")
        print(f"SMALL: first converged at {small_result['first_converged_relaxation']}")
        if run_medium:
            print(f"MEDIUM: first converged at {medium_result['first_converged_relaxation']}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--medium", action="store_true", help="Also run MEDIUM tier")
    parser.add_argument("--network", default=DEFAULT_NETWORK_SMALL, help="Network file path")
    args = parser.parse_args()

    result = run(network_file=args.network, run_medium=args.medium)
    print(json.dumps(result, indent=2, default=str))
