"""
Test A-2: Solve ACPF (Newton-Raphson) on TINY

Dimension: expressiveness
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Converges. Convergence residual must be reported and below the tool's
  stated tolerance. Number of NR iterations must be reported. Voltage magnitudes must
  differ from flat-start defaults (1.0 pu) on >95% of buses. Bus voltage magnitudes
  and angles, line P/Q flows, and losses accessible as structured output. If the tool
  cannot report iteration count or residual, document this as a diagnostic quality finding.
Solver: PyPSA internal Newton-Raphson (no external solver needed for ACPF)
Tool: PyPSA 1.1.2

NOTE: The shared matpower_loader's Patch 1 (transformer b = 1/x) is for DCPF B-matrix
  correctness. For ACPF, PyPSA's transformer 'b' field is the shunt susceptance (pi-model),
  NOT the series susceptance. Applying the DCPF patch breaks ACPF convergence completely.
  This test uses the raw import path without Patch 1.
"""

import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")


def load_network_for_acpf(network_file: str):
    """Load case39.m for ACPF — WITHOUT the DCPF transformer b patch.

    The shared matpower_loader applies b = 1/x to transformers, which is correct
    for the DCPF B-matrix but breaks ACPF because PyPSA's transformer 'b' field
    in the AC context is shunt susceptance (pi-model), not series susceptance.
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
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute AC Power Flow (Newton-Raphson) on IEEE 39-bus network.

    Follows convergence-protocol.md: flat-start first, DC warm start fallback if needed.

    Returns:
        dict with standard keys (status, wall_clock_seconds, details, errors, workarounds)
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
        # 1. Load network (flat start: v=1.0 pu, angle=0 is PyPSA default)
        n = load_network_for_acpf(network_file)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["flat_start_confirmed"] = True

        # 2. Attempt AC power flow (flat start)
        import tracemalloc

        tracemalloc.start()
        solve_start = time.perf_counter()
        pf_result = n.pf(x_tol=1e-6)
        solve_elapsed = time.perf_counter() - solve_start
        _current, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)

        # 3. Extract convergence information
        converged_all = False
        total_iters = None
        final_residual = None
        results["details"]["dc_warm_start_used"] = False

        if hasattr(pf_result, "keys"):
            results["details"]["pf_result_keys"] = list(pf_result.keys())

            if "converged" in pf_result:
                converged_all = bool(pf_result["converged"].values.flatten()[0])
            if "n_iter" in pf_result:
                total_iters = int(pf_result["n_iter"].values.flatten()[0])
            if "error" in pf_result:
                final_residual = float(pf_result["error"].values.flatten()[0])

        results["details"]["converged_flat_start"] = converged_all
        results["details"]["nr_iterations_flat_start"] = total_iters
        results["details"]["convergence_residual_flat_start"] = final_residual

        # If flat start failed, attempt DC warm start per convergence-protocol.md
        if not converged_all:
            results["workarounds"].append(
                "Flat start failed — applied DC warm start (angles from lpf(), magnitudes 1.0 pu)"
            )
            n2 = load_network_for_acpf(network_file)
            n2.lpf()
            # use_seed=True uses existing bus v_mag/v_ang as initialization
            solve_start2 = time.perf_counter()
            pf_result2 = n2.pf(x_tol=1e-6, use_seed=True)
            solve_elapsed2 = time.perf_counter() - solve_start2

            if hasattr(pf_result2, "keys"):
                if "converged" in pf_result2:
                    converged_all = bool(pf_result2["converged"].values.flatten()[0])
                if "n_iter" in pf_result2:
                    total_iters = int(pf_result2["n_iter"].values.flatten()[0])
                if "error" in pf_result2:
                    final_residual = float(pf_result2["error"].values.flatten()[0])

            if converged_all:
                n = n2
                # dc_warm_start_used = True  # tracked in results dict
                results["details"]["solve_seconds_warm_start"] = solve_elapsed2
                results["details"]["dc_warm_start_used"] = True

        results["details"]["converged"] = converged_all
        results["details"]["nr_iterations"] = total_iters
        results["details"]["convergence_residual"] = final_residual

        # 4. Extract and validate results
        v_mag_pu = n.buses_t.v_mag_pu
        v_ang = n.buses_t.v_ang
        p0 = n.lines_t.p0
        q0 = n.lines_t.q0

        assert isinstance(v_mag_pu, pd.DataFrame), "v_mag_pu should be DataFrame"
        assert isinstance(v_ang, pd.DataFrame), "v_ang should be DataFrame"
        assert isinstance(p0, pd.DataFrame), "p0 should be DataFrame"
        assert isinstance(q0, pd.DataFrame), "q0 should be DataFrame"

        v_mag_vals = v_mag_pu.iloc[0]

        # Convergence quality: >95% of buses must have v_mag != 1.0 pu
        n_non_flat = int(((v_mag_vals - 1.0).abs() > 0.001).sum())
        pct_non_flat = float(n_non_flat / len(n.buses) * 100)
        results["details"]["pct_buses_non_flat_voltage"] = pct_non_flat
        results["details"]["n_buses_non_flat"] = n_non_flat
        results["details"]["n_buses_total"] = len(n.buses)

        # Voltage statistics
        results["details"]["v_mag_min"] = float(v_mag_vals.min())
        results["details"]["v_mag_max"] = float(v_mag_vals.max())
        results["details"]["v_mag_mean"] = float(v_mag_vals.mean())

        # First-5 summaries
        results["details"]["v_mag_first5"] = v_mag_vals.head(5).to_dict()
        v_ang_vals = v_ang.iloc[0]
        results["details"]["v_ang_deg_first5"] = (v_ang_vals.head(5) * 180 / np.pi).to_dict()
        if len(p0.columns) > 0:
            results["details"]["p0_first5"] = p0.iloc[0].head(5).to_dict()
        if len(q0.columns) > 0:
            results["details"]["q0_first5"] = q0.iloc[0].head(5).to_dict()

        # Compute losses
        if len(p0) > 0 and len(n.lines_t.p1) > 0:
            p0_vals = p0.iloc[0]
            p1_vals = n.lines_t.p1.iloc[0]
            line_losses = (p0_vals + p1_vals).abs().sum()
            total_load = float(n.loads.p_set.sum())
            results["details"]["total_losses_mw"] = float(line_losses)
            results["details"]["total_load_mw"] = total_load
            results["details"]["loss_pct"] = (
                float(line_losses / total_load * 100) if total_load > 0 else 0.0
            )

        # Print key outputs
        print("=== Voltage Magnitudes (pu) — first 5 buses ===")
        print(v_mag_vals.head(5).to_string())
        print(f"\n=== V_mag range: {v_mag_vals.min():.6f} - {v_mag_vals.max():.6f} ===")
        print("\n=== Voltage Angles (degrees) — first 5 buses ===")
        print((v_ang_vals.head(5) * 180 / np.pi).to_string())
        print("\n=== Line P flows (MW) — first 5 lines ===")
        if len(p0.columns) > 0:
            print(p0.iloc[0].head(5).to_string())
        print("\n=== Line Q flows (MVAr) — first 5 lines ===")
        if len(q0.columns) > 0:
            print(q0.iloc[0].head(5).to_string())

        # 5. Pass condition check
        if not converged_all:
            results["errors"].append("ACPF did not converge (including DC warm start fallback)")
            results["status"] = "fail"
        elif pct_non_flat <= 95.0:
            results["errors"].append(
                f"Only {pct_non_flat:.1f}% of buses have non-flat voltages "
                f"(<95% required). Suspect trivial solution."
            )
            results["status"] = "fail"
        else:
            # Check diagnostic quality
            diag_issues = []
            if total_iters is None:
                diag_issues.append("NR iteration count not accessible — diagnostic quality finding")
            elif total_iters == 0:
                diag_issues.append("NR reported 0 iterations — solver may not have actually run")
            if final_residual is None:
                diag_issues.append(
                    "Convergence residual not accessible — diagnostic quality finding"
                )

            if diag_issues:
                results["errors"].extend([f"DIAGNOSTIC: {issue}" for issue in diag_issues])
                results["status"] = "qualified_pass"
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
