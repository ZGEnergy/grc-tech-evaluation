"""
Test A-2: AC Power Flow (acpf)

Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m, ~10000 buses)
Pass condition: Same as TINY. Extra: convergence quality on large network
  (iterations, residual). Non-convergence on MEDIUM is a finding, not automatic failure.
  Applies convergence verification protocol (flat start first, DC warm start fallback).
Tool: PyPSA 1.1.2
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc dict -> pypsa."""
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


def extract_pf_convergence(pf_result) -> tuple[bool, int | None, float | None]:
    """Extract convergence info from pf() result Dict."""
    converged = False
    n_iters = None
    residual = None

    try:
        if hasattr(pf_result, "keys"):
            if "converged" in pf_result:
                converged = bool(pf_result["converged"].values.flatten()[0])
            if "n_iter" in pf_result:
                n_iters = int(pf_result["n_iter"].values.flatten()[0])
            if "error" in pf_result:
                residual = float(pf_result["error"].values.flatten()[0])
    except Exception:
        pass

    return converged, n_iters, residual


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute AC Power Flow (Newton-Raphson) on ACTIVSg10k network.

    Follows convergence-protocol.md:
    1. Flat start (default)
    2. If flat start fails, DC warm start fallback
    Non-convergence on MEDIUM is a finding but not automatic failure.

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
        # 1. Load network (flat start: v=1.0 pu, angle=0 is PyPSA default)
        load_start = time.perf_counter()
        n = load_network(network_file)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["load_seconds"] = load_elapsed
        print(f"Network loaded: {len(n.buses)} buses in {load_elapsed:.3f}s")

        # 2. Attempt AC power flow (flat start) with memory tracking
        print("\n=== Attempting AC PF (flat start) ===")
        tracemalloc.start()
        solve_start = time.perf_counter()
        pf_result = n.pf()
        solve_elapsed = time.perf_counter() - solve_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds_flat_start"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)
        print(
            f"Flat start solve time: {solve_elapsed:.3f}s, peak mem: {peak_mem / (1024 * 1024):.1f} MB"
        )

        # 3. Extract convergence info
        converged, n_iters, residual = extract_pf_convergence(pf_result)
        results["details"]["flat_start_converged"] = converged
        results["details"]["flat_start_iterations"] = n_iters
        results["details"]["flat_start_residual"] = residual
        print(f"Flat start: converged={converged}, iterations={n_iters}, residual={residual}")

        # 4. If flat start failed, attempt DC warm start
        warm_start_used = False
        if not converged:
            print("\n=== Flat start failed — attempting DC warm start ===")
            results["workarounds"].append(
                "Flat start failed on MEDIUM network — applied DC warm start "
                "(angles from lpf(), magnitudes kept at 1.0 pu)"
            )
            warm_start_used = True

            # Load fresh network for warm start
            n2 = load_network(network_file)
            # Run DCPF to get angles
            n2.lpf()
            # Set initial angle estimates on buses
            for bus in n2.buses.index:
                if len(n2.buses_t.v_ang) > 0 and bus in n2.buses_t.v_ang.columns:
                    n2.buses.at[bus, "v_ang"] = float(n2.buses_t.v_ang.iloc[0][bus])

            ws_start = time.perf_counter()
            pf_result2 = n2.pf()
            ws_elapsed = time.perf_counter() - ws_start
            converged2, n_iters2, residual2 = extract_pf_convergence(pf_result2)
            results["details"]["warm_start_seconds"] = ws_elapsed
            results["details"]["warm_start_converged"] = converged2
            results["details"]["warm_start_iterations"] = n_iters2
            results["details"]["warm_start_residual"] = residual2
            print(
                f"DC warm start: converged={converged2}, iterations={n_iters2}, residual={residual2}"
            )

            if converged2:
                converged = True
                n_iters = n_iters2
                residual = residual2
                n = n2  # use warm-start network for result extraction

        results["details"]["final_converged"] = converged
        results["details"]["final_iterations"] = n_iters
        results["details"]["final_residual"] = residual
        results["details"]["warm_start_used"] = warm_start_used

        # 5. Extract voltage and flow results regardless of convergence
        v_mag_pu = n.buses_t.v_mag_pu
        v_ang = n.buses_t.v_ang
        p0 = n.lines_t.p0
        q0 = n.lines_t.q0

        if len(v_mag_pu) > 0:
            v_vals = v_mag_pu.iloc[0]
            n_buses = len(v_vals)
            non_flat_mask = (v_vals - 1.0).abs() > 0.001
            _n_non_flat = int(non_flat_mask.sum())
            pct_non_flat = float(non_flat_mask.mean()) * 100
            results["details"]["v_mag_min"] = float(v_vals.min())
            results["details"]["v_mag_max"] = float(v_vals.max())
            results["details"]["pct_buses_non_flat_voltage"] = pct_non_flat
            results["details"]["n_buses_non_flat"] = int(((v_vals - 1.0).abs() > 0.001).sum())
            results["details"]["v_mag_first5"] = v_vals.head(5).to_dict()
            print("\n=== Voltage Profile ===")
            print(f"  V_mag range: [{v_vals.min():.4f}, {v_vals.max():.4f}] pu")
            print(
                f"  Non-flat buses: {results['details']['n_buses_non_flat']}/{n_buses} ({pct_non_flat:.1f}%)"
            )
            print("  First 5 bus voltages:")
            print(v_vals.head(5).to_string())

        if len(v_ang) > 0:
            v_ang_deg = v_ang.iloc[0] * 180 / np.pi
            results["details"]["v_ang_deg_first5"] = v_ang_deg.head(5).to_dict()

        if len(p0) > 0 and len(p0.columns) > 0:
            p0_vals = p0.iloc[0]
            results["details"]["p0_first5"] = p0_vals.head(5).to_dict()
            results["details"]["max_line_flow_mw"] = float(p0_vals.abs().max())
            # Compute losses
            if len(n.lines_t.p1) > 0:
                p1_vals = n.lines_t.p1.iloc[0]
                total_losses = float((p0_vals + p1_vals).abs().sum())
                total_load = float(n.loads.p_set.sum())
                results["details"]["total_losses_mw"] = total_losses
                results["details"]["loss_pct"] = (
                    float(total_losses / total_load * 100) if total_load > 0 else None
                )

        if len(q0) > 0 and len(q0.columns) > 0:
            results["details"]["q0_first5"] = q0.iloc[0].head(5).to_dict()

        # 6. Pass condition evaluation
        # Non-convergence on MEDIUM is a finding, not automatic failure.
        # If flat start converges: pass
        # If DC warm start needed: qualified_pass
        # If neither converges: fail but with detailed finding
        if not converged:
            results["errors"].append(
                "ACPF did not converge on MEDIUM (10k-bus) network from flat start "
                "or DC warm start. This is a notable finding for large networks."
            )
            results["status"] = "fail"
        else:
            # Verify convergence quality
            if n_iters is not None and n_iters == 0:
                results["errors"].append("WARNING: 0 NR iterations — solver may not have run")
            if len(v_mag_pu) > 0:
                pct_non_flat_check = float((v_mag_pu.iloc[0] - 1.0).abs().gt(0.001).mean()) * 100
                if pct_non_flat_check < 95.0:
                    results["errors"].append(
                        f"Convergence quality: only {pct_non_flat_check:.1f}% buses have "
                        "non-flat voltages — possible trivial solution"
                    )

            if warm_start_used:
                results["status"] = "qualified_pass"
            elif len(results["errors"]) == 0:
                results["status"] = "pass"
            else:
                results["status"] = "qualified_pass"

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
