"""
Test G-FNM-4: ACPF convergence — DCPF warm-start + progressive relaxation

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: No hard pass/fail gate. All outcomes are diagnostic findings.
    Record relaxation_level_achieved: 0%, 10%, 20%, or infeasible.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import time
import traceback

import numpy as np


def run(
    case_file: str = "/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
) -> dict:
    """Execute the G-FNM-4 ACPF convergence test.

    Uses DCPF warm-start followed by progressive thermal limit relaxation.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "informational",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import tracemalloc

        import pandapower as pp
        from matpowercaseframes import CaseFrames
        from pandapower.converter.pypower.from_ppc import from_ppc

        tracemalloc.start()

        # --- Step 1: Load FNM and solve DCPF for warm-start ---
        cf = CaseFrames(case_file)
        branch = cf.branch.values.copy()

        # Workaround: set zero RATE_A to 9999 (same as G-FNM-1/G-FNM-3)
        rate_a_col = 5
        zero_rate_mask = np.isclose(branch[:, rate_a_col], 0)
        branch[zero_rate_mask, rate_a_col] = 9999.0

        ppc = {
            "version": "2",
            "baseMVA": cf.baseMVA,
            "bus": cf.bus.values,
            "gen": cf.gen.values,
            "branch": branch,
        }

        t_load_start = time.perf_counter()
        net = from_ppc(ppc, f_hz=60)
        t_load = time.perf_counter() - t_load_start

        results["details"]["load_time_seconds"] = t_load
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["input_path"] = "matpower"
        results["details"]["baseMVA"] = net.sn_mva

        # Solve DCPF
        t_dcpf_start = time.perf_counter()
        pp.rundcpp(net)
        t_dcpf = time.perf_counter() - t_dcpf_start

        if not net["converged"]:
            results["errors"].append("DCPF did not converge — cannot warm-start ACPF")
            return results

        results["details"]["dcpf_solve_seconds"] = t_dcpf

        # Extract DCPF solution angles for warm-start diagnostics
        dcpf_va_deg = net.res_bus["va_degree"].values
        valid_angles = dcpf_va_deg[np.isfinite(dcpf_va_deg)]

        dcpf_mean_deg = float(np.mean(np.abs(valid_angles)))
        dcpf_max_abs_deg = float(np.max(np.abs(valid_angles)))

        results["details"]["dcpf_init_mean_deg"] = dcpf_mean_deg
        results["details"]["dcpf_init_max_abs_deg"] = dcpf_max_abs_deg
        results["details"]["dcpf_converged"] = True

        # --- Store original thermal limits for relaxation ---
        # pandapower stores thermal limits in line.max_i_ka, trafo.sn_mva, impedance
        # We track them for progressive relaxation.
        orig_line_max_i = net.line["max_i_ka"].copy()
        orig_trafo_sn = net.trafo["sn_mva"].copy()
        orig_impedance_sn = net.impedance["sn_mva"].copy()

        # --- ACPF convergence attempt function ---
        def attempt_acpf(net_obj, relaxation_label, timeout_seconds=1800):
            """Attempt ACPF with init='results' (DCPF warm-start).

            Returns (converged, solve_time, iterations, error_msg).
            """
            t_start = time.perf_counter()
            try:
                pp.runpp(
                    net_obj,
                    init="results",
                    algorithm="nr",
                    max_iteration=100,
                    tolerance_mva=1e-6,
                    enforce_q_lims=True,
                    numba=True,
                )
                elapsed = time.perf_counter() - t_start
                converged = net_obj["converged"]
                # pandapower stores NR iteration count internally
                nr_iters = getattr(net_obj, "_ppc", {}).get("iterations", None)
                return converged, elapsed, nr_iters, None
            except Exception as e:
                elapsed = time.perf_counter() - t_start
                return False, elapsed, None, f"{type(e).__name__}: {e}"

        # --- Step 2: ACPF at 0% relaxation ---
        converged_0, time_0, iters_0, err_0 = attempt_acpf(net, "0%")

        step2 = {
            "relaxation": "0%",
            "converged": converged_0,
            "wall_clock_seconds": time_0,
            "iterations": iters_0,
            "error": err_0,
        }
        results["details"]["step2_0pct"] = step2

        if converged_0:
            results["details"]["relaxation_level_achieved"] = "0%"
            # Record voltage statistics
            vm_pu = net.res_bus["vm_pu"].values
            valid_vm = vm_pu[np.isfinite(vm_pu)]
            results["details"]["acpf_vm_mean"] = float(np.mean(valid_vm))
            results["details"]["acpf_vm_min"] = float(np.min(valid_vm))
            results["details"]["acpf_vm_max"] = float(np.max(valid_vm))
            results["details"]["acpf_vm_std"] = float(np.std(valid_vm))
            non_flat = np.sum(np.abs(valid_vm - 1.0) > 0.001)
            results["details"]["acpf_non_flat_pct"] = float(non_flat / len(valid_vm) * 100)
        else:
            # --- Step 3: ACPF at 10% relaxation ---
            # Restore DCPF warm-start by re-solving DCPF
            pp.rundcpp(net)

            # Relax thermal limits by 10%
            net.line["max_i_ka"] = orig_line_max_i * 1.10
            net.trafo["sn_mva"] = orig_trafo_sn * 1.10
            net.impedance["sn_mva"] = orig_impedance_sn * 1.10

            converged_10, time_10, iters_10, err_10 = attempt_acpf(net, "10%")

            step3 = {
                "relaxation": "10%",
                "converged": converged_10,
                "wall_clock_seconds": time_10,
                "iterations": iters_10,
                "error": err_10,
            }
            results["details"]["step3_10pct"] = step3

            if converged_10:
                results["details"]["relaxation_level_achieved"] = "10%"
                vm_pu = net.res_bus["vm_pu"].values
                valid_vm = vm_pu[np.isfinite(vm_pu)]
                results["details"]["acpf_vm_mean"] = float(np.mean(valid_vm))
                results["details"]["acpf_vm_min"] = float(np.min(valid_vm))
                results["details"]["acpf_vm_max"] = float(np.max(valid_vm))
                results["details"]["acpf_vm_std"] = float(np.std(valid_vm))
                non_flat = np.sum(np.abs(valid_vm - 1.0) > 0.001)
                results["details"]["acpf_non_flat_pct"] = float(non_flat / len(valid_vm) * 100)
            else:
                # --- Step 4: ACPF at 20% relaxation ---
                # Re-solve DCPF for warm-start
                # Reset limits first
                net.line["max_i_ka"] = orig_line_max_i
                net.trafo["sn_mva"] = orig_trafo_sn
                net.impedance["sn_mva"] = orig_impedance_sn
                pp.rundcpp(net)

                # Relax by 20%
                net.line["max_i_ka"] = orig_line_max_i * 1.20
                net.trafo["sn_mva"] = orig_trafo_sn * 1.20
                net.impedance["sn_mva"] = orig_impedance_sn * 1.20

                converged_20, time_20, iters_20, err_20 = attempt_acpf(net, "20%")

                step4 = {
                    "relaxation": "20%",
                    "converged": converged_20,
                    "wall_clock_seconds": time_20,
                    "iterations": iters_20,
                    "error": err_20,
                }
                results["details"]["step4_20pct"] = step4

                if converged_20:
                    results["details"]["relaxation_level_achieved"] = "20%"
                    vm_pu = net.res_bus["vm_pu"].values
                    valid_vm = vm_pu[np.isfinite(vm_pu)]
                    results["details"]["acpf_vm_mean"] = float(np.mean(valid_vm))
                    results["details"]["acpf_vm_min"] = float(np.min(valid_vm))
                    results["details"]["acpf_vm_max"] = float(np.max(valid_vm))
                    results["details"]["acpf_vm_std"] = float(np.std(valid_vm))
                    non_flat = np.sum(np.abs(valid_vm - 1.0) > 0.001)
                    results["details"]["acpf_non_flat_pct"] = float(non_flat / len(valid_vm) * 100)
                else:
                    results["details"]["relaxation_level_achieved"] = "infeasible"

        # Peak memory
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)

        # Record workarounds
        results["workarounds"] = [
            "MATPOWER fallback: used pre-cleaned fnm_main_island.m instead of "
            "intermediate CSVs (pandapower has no native CSV import).",
            "Zero RATE_A branches set to 9999 before from_ppc (same as G-FNM-1).",
        ]

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
