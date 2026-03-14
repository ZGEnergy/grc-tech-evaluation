"""
Test G-FNM-4: ACPF convergence test -- DCPF warm-start + progressive relaxation on FNM

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: No hard pass/fail gate. All outcomes are diagnostic findings. Record
    relaxation_level_achieved: 0%, 10%, 20%, or infeasible.
Tool: gridcal (VeraGrid) v5.6.28

Input: MATPOWER fallback path (G-FNM-1 CSV ingestion failed).
File: data/fnm/reference/cleaned/fnm_main_island.m

Note: Branch rate relaxation (10%, 20%) does not affect ACPF convergence because
thermal ratings constrain OPF dispatch, not the power flow equations themselves.
The relaxation steps are executed per protocol but produce identical ACPF results.
"""

from __future__ import annotations

import csv
import json
import time
import traceback

import numpy as np


def angle_diff_deg(a: float, b: float) -> float:
    """Compute signed angle difference normalized to [-180, 180]."""
    d = a - b
    return ((d + 180) % 360) - 180


def run(
    matpower_file: str = "/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
    ref_bus_file: str = "/workspace/data/fnm/reference/acpf/buses_acpf.csv",
    pass_conditions_file: str = "/workspace/data/fnm/reference/pass_conditions.json",
) -> dict:
    """Execute G-FNM-4 and return structured results."""
    results: dict = {
        "status": "informational",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import tracemalloc

        tracemalloc.start()

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        results["details"]["veragrid_version"] = getattr(vge, "__version__", "unknown")
        results["details"]["input_path"] = "matpower"

        # ==================================================================
        # Step 1: Load network and solve DCPF for warm start
        # ==================================================================
        t_load_start = time.perf_counter()
        grid = vge.open_file(matpower_file)
        t_load = time.perf_counter() - t_load_start

        if grid is None:
            results["errors"].append("open_file returned None for MATPOWER file")
            return results

        results["details"]["load_time_seconds"] = round(t_load, 3)
        results["details"]["bus_count"] = len(grid.buses)
        results["details"]["branch_count"] = len(grid.get_branches())
        results["details"]["sbase"] = grid.Sbase

        # Solve DCPF
        dc_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        t_dc_start = time.perf_counter()
        dc_results = vge.power_flow(grid, dc_opts)
        t_dc = time.perf_counter() - t_dc_start

        dc_angles_deg = np.angle(dc_results.voltage, deg=True)
        dc_angles_rad = np.angle(dc_results.voltage, deg=False)
        nonzero_dc = int(np.count_nonzero(dc_angles_deg))
        dc_mean_deg = float(np.mean(np.abs(dc_angles_deg)))
        dc_max_abs_deg = float(np.max(np.abs(dc_angles_deg)))

        results["details"]["dcpf_solve_time_seconds"] = round(t_dc, 3)
        results["details"]["dcpf_nonzero_angle_buses"] = nonzero_dc
        results["details"]["dcpf_init_mean_deg"] = round(dc_mean_deg, 4)
        results["details"]["dcpf_init_max_abs_deg"] = round(dc_max_abs_deg, 4)

        if nonzero_dc < len(grid.buses) * 0.5:
            results["errors"].append(
                f"DCPF trivial solution: only {nonzero_dc}/{len(grid.buses)} "
                "buses have nonzero angles"
            )
            results["details"]["relaxation_level_achieved"] = "infeasible"
            return results

        # ==================================================================
        # Step 2: Set DCPF warm-start initial conditions
        # ==================================================================
        buses = grid.buses
        for i, bus in enumerate(buses):
            bus.Vm0 = 1.0
            bus.Va0 = float(dc_angles_rad[i])

        results["details"]["warm_start_applied"] = True

        # ==================================================================
        # Step 3: ACPF attempts -- multiple solvers, progressive relaxation
        # ==================================================================
        all_branches = grid.get_branches()
        original_rates = [br.rate for br in all_branches]

        relaxation_levels = [
            ("0%", 1.00),
            ("10%", 1.10),
            ("20%", 1.20),
        ]

        # Solver configurations to try at each relaxation level
        solver_configs = [
            {
                "name": "NR_no_retry",
                "solver_type": SolverType.NR,
                "retry_with_other_methods": False,
                "max_iter": 200,
                "control_q": False,
                "control_taps_modules": False,
                "control_taps_phase": False,
                "control_remote_voltage": False,
            },
            {
                "name": "NR_with_controls",
                "solver_type": SolverType.NR,
                "retry_with_other_methods": False,
                "max_iter": 200,
                "control_q": True,
                "control_taps_modules": True,
                "control_taps_phase": True,
                "control_remote_voltage": True,
            },
            {
                "name": "LM",
                "solver_type": SolverType.LM,
                "retry_with_other_methods": False,
                "max_iter": 200,
                "control_q": False,
                "control_taps_modules": False,
                "control_taps_phase": False,
                "control_remote_voltage": False,
            },
            {
                "name": "HELM",
                "solver_type": SolverType.HELM,
                "retry_with_other_methods": False,
                "max_iter": 100,
                "control_q": False,
                "control_taps_modules": False,
                "control_taps_phase": False,
                "control_remote_voltage": False,
            },
        ]

        relaxation_achieved = "infeasible"
        acpf_attempts = []
        best_converged_results = None

        for relax_label, rate_multiplier in relaxation_levels:
            # Apply rate multiplier
            for j, br in enumerate(all_branches):
                br.rate = original_rates[j] * rate_multiplier

            for solver_cfg in solver_configs:
                attempt_info: dict = {
                    "relaxation_level": relax_label,
                    "rate_multiplier": rate_multiplier,
                    "solver": solver_cfg["name"],
                }

                # Re-apply warm start
                for i, bus in enumerate(buses):
                    bus.Vm0 = 1.0
                    bus.Va0 = float(dc_angles_rad[i])

                ac_opts = vge.PowerFlowOptions(
                    solver_type=solver_cfg["solver_type"],
                    initialize_with_existing_solution=True,
                    retry_with_other_methods=solver_cfg["retry_with_other_methods"],
                    max_iter=solver_cfg["max_iter"],
                    tolerance=1e-6,
                    control_q=solver_cfg["control_q"],
                    control_taps_modules=solver_cfg["control_taps_modules"],
                    control_taps_phase=solver_cfg["control_taps_phase"],
                    control_remote_voltage=solver_cfg["control_remote_voltage"],
                )

                t_ac_start = time.perf_counter()
                try:
                    ac_results = vge.power_flow(grid, ac_opts)
                    t_ac = time.perf_counter() - t_ac_start

                    converged_raw = ac_results.converged
                    iterations = (
                        int(ac_results.iterations) if hasattr(ac_results, "iterations") else None
                    )
                    convergence_residual = (
                        float(ac_results.error) if hasattr(ac_results, "error") else None
                    )

                    V_ac = ac_results.voltage
                    vm_ac = np.abs(V_ac)

                    # Verify convergence quality
                    true_converged = bool(converged_raw)
                    convergence_quality = "genuine"
                    if true_converged:
                        if convergence_residual is not None and convergence_residual > 1.0:
                            true_converged = False
                            convergence_quality = (
                                f"false_convergence: residual={convergence_residual:.4f} "
                                "exceeds 1.0 tolerance"
                            )
                        elif iterations is not None and iterations <= 1:
                            if convergence_residual is not None and convergence_residual > 1e-4:
                                true_converged = False
                                convergence_quality = (
                                    f"suspect: 1 iteration with residual={convergence_residual:.4f}"
                                )

                    attempt_info.update(
                        {
                            "converged_reported": bool(converged_raw),
                            "converged_verified": true_converged,
                            "convergence_quality": convergence_quality,
                            "iterations": iterations,
                            "convergence_residual": convergence_residual,
                            "wall_clock_seconds": round(t_ac, 3),
                            "vm_mean": round(float(np.mean(vm_ac)), 6),
                            "vm_std": round(float(np.std(vm_ac)), 6),
                            "vm_min": round(float(np.min(vm_ac)), 6),
                            "vm_max": round(float(np.max(vm_ac)), 6),
                        }
                    )

                    if true_converged:
                        relaxation_achieved = relax_label
                        best_converged_results = ac_results

                except Exception as e:
                    t_ac = time.perf_counter() - t_ac_start
                    attempt_info.update(
                        {
                            "converged_reported": False,
                            "converged_verified": False,
                            "wall_clock_seconds": round(t_ac, 3),
                            "error": f"{type(e).__name__}: {e}",
                        }
                    )

                acpf_attempts.append(attempt_info)

            # If we found a genuine convergence, stop
            if relaxation_achieved != "infeasible":
                break

        # Restore original rates
        for j, br in enumerate(all_branches):
            br.rate = original_rates[j]

        results["details"]["relaxation_level_achieved"] = relaxation_achieved
        results["details"]["acpf_attempts"] = acpf_attempts

        # ==================================================================
        # Step 4: Reference comparison (if any genuine convergence)
        # ==================================================================
        if best_converged_results is not None:
            try:
                with open(ref_bus_file) as f:
                    reader = csv.DictReader(f)
                    ref_data = {}
                    for r in reader:
                        ref_data[int(r["bus_number"])] = {
                            "vm_pu": float(r["vm_pu"]),
                            "va_deg": float(r["va_deg"]),
                        }

                bus_codes = [int(b.code) for b in buses]
                V_final = best_converged_results.voltage
                vm_final = np.abs(V_final)
                va_final = np.angle(V_final, deg=True)

                vm_devs = []
                va_devs = []
                vm_pass = 0
                va_pass = 0
                both_pass = 0
                compared = 0

                for i, bnum in enumerate(bus_codes):
                    if bnum not in ref_data:
                        continue
                    compared += 1
                    ref_vm = ref_data[bnum]["vm_pu"]
                    ref_va = ref_data[bnum]["va_deg"]
                    d_vm = abs(float(vm_final[i]) - ref_vm)
                    d_va = abs(angle_diff_deg(float(va_final[i]), ref_va))
                    vm_devs.append(d_vm)
                    va_devs.append(d_va)
                    if d_vm < 0.005:
                        vm_pass += 1
                    if d_va < 0.5:
                        va_pass += 1
                    if d_vm < 0.005 and d_va < 0.5:
                        both_pass += 1

                if compared > 0:
                    results["details"]["acpf_reference_comparison"] = {
                        "buses_compared": compared,
                        "vm_passing": vm_pass,
                        "vm_pass_fraction": round(vm_pass / compared, 6),
                        "vm_mean_dev_pu": round(float(np.mean(vm_devs)), 6),
                        "vm_max_dev_pu": round(float(np.max(vm_devs)), 6),
                        "va_passing": va_pass,
                        "va_pass_fraction": round(va_pass / compared, 6),
                        "va_mean_dev_deg": round(float(np.mean(va_devs)), 4),
                        "va_max_dev_deg": round(float(np.max(va_devs)), 4),
                        "both_passing": both_pass,
                        "both_pass_fraction": round(both_pass / compared, 6),
                    }
            except Exception as ref_err:
                results["details"]["acpf_reference_comparison"] = {
                    "error": f"{type(ref_err).__name__}: {ref_err}",
                }

        # Memory
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["details"]["peak_memory_mb"] = round(peak / (1024 * 1024), 1)

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 3)

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
