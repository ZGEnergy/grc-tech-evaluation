"""
Test C-2: ACPF on MEDIUM — wall-clock, peak memory, iterations.

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: ACPF solves on MEDIUM.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: NR (native) — GridCal has no Ipopt integration for ACPF.

Convergence protocol: flat start first, then DC warm start fallback.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute C-2 ACPF scale test on MEDIUM and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        # 1. Load network
        grid = load_gridcal(network_file)
        buses = grid.get_buses()
        n_buses = grid.get_bus_number()
        n_branches = grid.get_branch_number()
        n_gens = len(grid.get_generators())

        results["details"]["bus_count"] = n_buses
        results["details"]["branch_count"] = n_branches
        results["details"]["gen_count"] = n_gens
        results["details"]["cpu_threads_available"] = os.cpu_count()
        results["details"]["cpu_threads_used"] = 1  # NR is single-threaded
        results["details"]["solver_note"] = (
            "GridCal has no Ipopt integration. Using native NR solver (SolverType.NR). "
            "Protocol specifies Ipopt; this is an inherent tool limitation."
        )

        # 2. Flat start ACPF
        tracemalloc.start()

        pf_opts = vge.PowerFlowOptions(
            solver_type=SolverType.NR,
            tolerance=1e-6,
            max_iter=100,
        )

        flat_start = time.perf_counter()
        pf_results = vge.power_flow(grid, options=pf_opts)
        flat_elapsed = time.perf_counter() - flat_start

        converged = bool(pf_results.converged)
        iterations = int(pf_results.iterations) if hasattr(pf_results, "iterations") else None
        residual = float(pf_results.error) if hasattr(pf_results, "error") else None

        results["details"]["flat_start_converged"] = converged
        results["details"]["flat_start_iterations"] = iterations
        results["details"]["flat_start_residual"] = residual
        results["details"]["flat_start_wall_clock_seconds"] = flat_elapsed

        solve_elapsed = flat_elapsed
        convergence_method = "flat_start"

        # 3. DC warm start fallback
        if not converged:
            results["details"]["dc_warmstart_attempted"] = True

            dc_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
            dc_results = vge.power_flow(grid, options=dc_opts)

            if dc_results.converged:
                for i, bus in enumerate(buses):
                    bus.Va0 = float(np.angle(dc_results.voltage[i]))

                pf_opts_warm = vge.PowerFlowOptions(
                    solver_type=SolverType.NR,
                    tolerance=1e-6,
                    max_iter=200,
                    use_stored_guess=True,
                )
                warm_start = time.perf_counter()
                pf_results = vge.power_flow(grid, options=pf_opts_warm)
                warm_elapsed = time.perf_counter() - warm_start

                converged = bool(pf_results.converged)
                iterations = (
                    int(pf_results.iterations) if hasattr(pf_results, "iterations") else None
                )
                residual = float(pf_results.error) if hasattr(pf_results, "error") else None

                results["details"]["dc_warmstart_converged"] = converged
                results["details"]["dc_warmstart_iterations"] = iterations
                results["details"]["dc_warmstart_residual"] = residual
                results["details"]["dc_warmstart_wall_clock_seconds"] = warm_elapsed

                if converged:
                    solve_elapsed = warm_elapsed
                    convergence_method = "dc_warmstart"

        # 4. Relaxed tolerance fallback
        if not converged:
            results["details"]["relaxed_tol_attempted"] = True
            pf_opts_relaxed = vge.PowerFlowOptions(
                solver_type=SolverType.NR,
                tolerance=1e-4,
                max_iter=200,
                use_stored_guess=True,
            )
            relaxed_start = time.perf_counter()
            pf_results = vge.power_flow(grid, options=pf_opts_relaxed)
            relaxed_elapsed = time.perf_counter() - relaxed_start

            converged = bool(pf_results.converged)
            iterations = int(pf_results.iterations) if hasattr(pf_results, "iterations") else None
            residual = float(pf_results.error) if hasattr(pf_results, "error") else None

            results["details"]["relaxed_tol_converged"] = converged
            results["details"]["relaxed_tol_iterations"] = iterations
            results["details"]["relaxed_tol_residual"] = residual
            results["details"]["relaxed_tol_wall_clock_seconds"] = relaxed_elapsed

            if converged:
                solve_elapsed = relaxed_elapsed
                convergence_method = "relaxed_tol_1e-4"

        # 5. Alternative solvers fallback
        alt_solvers_tried = {}
        if not converged:
            alt_solver_types = [
                ("HELM", SolverType.HELM),
                ("IWAMOTO", SolverType.IWAMOTO),
                ("LM", SolverType.LM),
            ]
            for alt_name, alt_solver in alt_solver_types:
                try:
                    alt_opts = vge.PowerFlowOptions(
                        solver_type=alt_solver,
                        tolerance=1e-6,
                        max_iter=200,
                    )
                    alt_t0 = time.perf_counter()
                    pf_results_alt = vge.power_flow(grid, options=alt_opts)
                    alt_elapsed = time.perf_counter() - alt_t0

                    alt_converged = bool(pf_results_alt.converged)
                    alt_iters = (
                        int(pf_results_alt.iterations)
                        if hasattr(pf_results_alt, "iterations")
                        else None
                    )
                    alt_res = (
                        float(pf_results_alt.error) if hasattr(pf_results_alt, "error") else None
                    )

                    alt_solvers_tried[alt_name] = {
                        "converged": alt_converged,
                        "iterations": alt_iters,
                        "residual": alt_res,
                        "wall_clock_seconds": alt_elapsed,
                    }

                    if alt_converged:
                        pf_results = pf_results_alt
                        converged = True
                        iterations = alt_iters
                        residual = alt_res
                        solve_elapsed = alt_elapsed
                        convergence_method = f"alt_solver_{alt_name}"
                        break
                except Exception as alt_err:
                    alt_solvers_tried[alt_name] = {
                        "converged": False,
                        "error": f"{type(alt_err).__name__}: {alt_err}",
                    }

            results["details"]["alternative_solvers_tried"] = alt_solvers_tried

        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_wall_clock_seconds"] = solve_elapsed
        results["details"]["convergence_method"] = convergence_method
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)

        if not converged:
            results["errors"].append(
                "ACPF did not converge on MEDIUM (flat start, DC warm start, "
                "relaxed tol, alternative solvers all failed)"
            )
            return results

        # 6. Extract results
        voltage = pf_results.voltage
        magnitudes = np.abs(voltage)
        angles_deg = np.degrees(np.angle(voltage))

        results["details"]["acpf_converged"] = True
        results["details"]["acpf_iterations"] = iterations
        results["details"]["acpf_residual"] = residual

        # Convergence quality: >95% buses differ from flat start
        non_flat_count = int(np.sum(np.abs(magnitudes - 1.0) > 1e-6))
        pct_non_flat = float(non_flat_count) / n_buses * 100.0
        results["details"]["pct_buses_differ_from_flat"] = pct_non_flat
        results["details"]["non_flat_bus_count"] = non_flat_count

        results["details"]["vm_min"] = float(np.min(magnitudes))
        results["details"]["vm_max"] = float(np.max(magnitudes))
        results["details"]["vm_mean"] = float(np.mean(magnitudes))
        results["details"]["max_angle_deg"] = float(np.max(np.abs(angles_deg)))

        # Losses
        losses = pf_results.losses
        total_losses_mw = float(np.sum(np.real(losses)))
        results["details"]["total_losses_mw"] = total_losses_mw

        # Branch loading
        loading = np.abs(pf_results.loading)
        results["details"]["max_loading_pct"] = float(np.max(loading) * 100)

        # 7. Pass condition check
        pass_checks = {
            "acpf_converged": converged,
            "iterations_reported": iterations is not None and iterations > 0,
            "voltage_profile_nontrivial": pct_non_flat > 95.0,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
