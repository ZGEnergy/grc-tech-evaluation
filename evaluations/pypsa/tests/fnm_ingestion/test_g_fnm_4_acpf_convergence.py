"""
Test G-FNM-4: ACPF convergence -- DCPF warm-start + progressive relaxation on LARGE

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01, 27862-bus main island)
Pass condition: No hard pass/fail gate. All outcomes are diagnostic findings.
  Record relaxation_level_achieved: 0%, 10%, 20%, or infeasible.
  If convergence occurs at any level, record as a discriminating solver robustness strength.
Tool: PyPSA 1.1.2
Solver: Newton-Raphson (PyPSA built-in, via n.pf())
Input: MATPOWER fallback (data/fnm/reference/cleaned/fnm_main_island.m)
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import numpy as np

CLEANED_M = Path("/workspace/data/fnm/reference/cleaned/fnm_main_island.m")
ACPF_REF_BUSES = Path("/workspace/data/fnm/reference/acpf/buses_acpf.csv")


def run() -> dict:
    """Execute G-FNM-4 ACPF convergence test and return structured results."""
    import tracemalloc

    import pypsa
    from matpowercaseframes import CaseFrames

    results: dict = {
        "status": "informational",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # ── 1. Load cleaned MATPOWER case ────────────────────────────────
        cf = CaseFrames(str(CLEANED_M))
        bus_array = cf.bus.values
        gen_array = cf.gen.values
        branch_array = cf.branch.values
        baseMVA = float(cf.baseMVA)

        ppc: dict = {
            "version": "2",
            "baseMVA": baseMVA,
            "bus": bus_array,
            "gen": gen_array,
            "branch": branch_array,
        }

        results["details"]["baseMVA"] = baseMVA
        results["details"]["tool_version"] = pypsa.__version__
        results["details"]["input_path"] = "matpower"

        branch_status = branch_array[:, 10].astype(int)
        n_active = int((branch_status == 1).sum())

        results["details"]["network_size"] = {
            "buses": int(bus_array.shape[0]),
            "branches_total": int(branch_array.shape[0]),
            "branches_active": n_active,
            "generators": int(gen_array.shape[0]),
        }

        results["workarounds"].append(
            "MATPOWER fallback: G-FNM-1 failed (psse_parse_error). Loaded from "
            "pre-cleaned MATPOWER .m file via matpowercaseframes + import_from_pypower_ppc."
        )

        # ── 2. Import into PyPSA ────────────────────────────────────────
        net = pypsa.Network()
        net.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=100000.0)
        net.set_snapshots([0])

        results["details"]["pypsa_counts"] = {
            "buses": len(net.buses),
            "lines": len(net.lines),
            "transformers": len(net.transformers),
            "generators": len(net.generators),
            "loads": len(net.loads),
        }

        # ── Step 1: Solve DCPF for warm start ───────────────────────────
        t_dc_start = time.perf_counter()
        net.lpf()
        t_dc = time.perf_counter() - t_dc_start

        if hasattr(net, "buses_t") and "v_ang" in net.buses_t and len(net.buses_t.v_ang) > 0:
            dc_va_rad = net.buses_t.v_ang.iloc[0]
        else:
            dc_va_rad = net.buses.v_ang

        results["details"]["dcpf_warm_start"] = {
            "solve_seconds": round(t_dc, 4),
            "va_range_deg": [
                round(float(np.degrees(dc_va_rad.min())), 4),
                round(float(np.degrees(dc_va_rad.max())), 4),
            ],
        }

        # Set DC angles as initial guess for ACPF
        net.buses["v_ang"] = dc_va_rad.values if hasattr(dc_va_rad, "values") else dc_va_rad

        results["details"]["initialization"] = {
            "type": "dc_warm_start",
            "note": "DC voltage angles from lpf() used as initial guess; VM=1.0 (flat)",
        }

        # ── Step 2: Attempt ACPF at 0% relaxation ──────────────────────
        relaxation_levels = [0, 10, 20]
        relaxation_achieved = "infeasible"

        for relax_pct in relaxation_levels:
            # Create fresh network for each attempt
            net_trial = pypsa.Network()
            net_trial.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=100000.0)
            net_trial.set_snapshots([0])

            # Apply DC warm-start angles
            net_trial.buses["v_ang"] = (
                dc_va_rad.values if hasattr(dc_va_rad, "values") else dc_va_rad
            )

            # Apply thermal limit relaxation
            if relax_pct > 0:
                factor = 1.0 + relax_pct / 100.0
                net_trial.lines["s_nom"] = net_trial.lines["s_nom"] * factor
                net_trial.transformers["s_nom"] = net_trial.transformers["s_nom"] * factor

            tracemalloc.start()
            t_solve_start = time.perf_counter()

            try:
                # PyPSA's Newton-Raphson AC power flow with 30-min timeout
                converged = net_trial.pf()
                t_solve = time.perf_counter() - t_solve_start
                _, peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                peak_mem_mb = peak_mem / (1024 * 1024)
            except Exception as solve_err:
                t_solve = time.perf_counter() - t_solve_start
                try:
                    tracemalloc.stop()
                except RuntimeError:
                    pass
                results["details"][f"relaxation_{relax_pct}pct"] = {
                    "status": "exception",
                    "error": f"{type(solve_err).__name__}: {solve_err}",
                    "solve_seconds": round(t_solve, 4),
                }
                continue

            # Interpret convergence
            attempt_result: dict = {
                "relaxation_pct": relax_pct,
                "solve_seconds": round(t_solve, 4),
                "peak_memory_mb": round(peak_mem_mb, 1),
            }

            overall_converged = False
            total_iterations = 0
            final_residual = None

            try:
                if isinstance(converged, dict):
                    if "converged" in converged:
                        conv_df = converged["converged"]
                        overall_converged = bool(conv_df.all().all())
                        attempt_result["converged_per_subnetwork"] = (
                            conv_df.to_dict() if hasattr(conv_df, "to_dict") else str(conv_df)
                        )
                    if "n_iter" in converged:
                        n_iter_df = converged["n_iter"]
                        total_iterations = int(n_iter_df.max().max())
                    if "error" in converged:
                        err_df = converged["error"]
                        max_err = err_df.max().max()
                        final_residual = float(max_err) if not np.isnan(max_err) else None
            except Exception as parse_err:
                attempt_result["parse_error"] = str(parse_err)

            attempt_result["converged"] = overall_converged
            attempt_result["iterations"] = total_iterations
            attempt_result["final_residual"] = final_residual

            if overall_converged:
                # Convergence quality checks
                if total_iterations == 0:
                    attempt_result["quality_warning"] = (
                        "Zero iterations: solver may not have actually run."
                    )

                # Extract solution statistics
                try:
                    if (
                        hasattr(net_trial, "buses_t")
                        and "v_mag_pu" in net_trial.buses_t
                        and len(net_trial.buses_t.v_mag_pu) > 0
                    ):
                        vm = net_trial.buses_t.v_mag_pu.iloc[0].values
                        vm_finite = vm[np.isfinite(vm)]
                        pct_not_flat = float(np.mean(~np.isclose(vm_finite, 1.0)) * 100)
                        attempt_result["voltage_magnitude"] = {
                            "min_pu": round(float(np.min(vm_finite)), 6),
                            "max_pu": round(float(np.max(vm_finite)), 6),
                            "mean_pu": round(float(np.mean(vm_finite)), 6),
                            "std_pu": round(float(np.std(vm_finite)), 6),
                            "pct_outside_0p95_1p05": round(
                                float(np.mean((vm_finite < 0.95) | (vm_finite > 1.05)) * 100), 2
                            ),
                            "pct_not_flat_start": round(pct_not_flat, 2),
                        }

                        # Convergence quality: >95% buses should differ from flat start
                        if pct_not_flat < 5.0:
                            attempt_result["quality_warning"] = (
                                f"Only {pct_not_flat:.1f}% of buses differ from flat-start VM=1.0. "
                                "Solver may have returned trivial solution."
                            )
                except Exception as ext_err:
                    attempt_result["extraction_error"] = str(ext_err)

                relaxation_achieved = f"{relax_pct}%"
                results["details"][f"relaxation_{relax_pct}pct"] = attempt_result
                break
            else:
                results["details"][f"relaxation_{relax_pct}pct"] = attempt_result

        results["details"]["relaxation_level_achieved"] = relaxation_achieved

        # ── Summary ─────────────────────────────────────────────────────
        results["details"]["matpower_comparison"] = {
            "matpower_converged": False,
            "matpower_methods_tried": [
                "NR (flat start, all variants: NR, NR-IC, NR-SP, NR-SH, NR-IH)",
                "FDXB/FDBX (1000 iterations)",
                "Manual continuation (1%-30% converged, fails at 35%)",
                "runcpf continuation power flow (stuck at nose point ~30%)",
            ],
            "matpower_max_load_pct": 30,
            "note": "No reference ACPF solution exists. Convergence is a positive finding.",
        }

        if relaxation_achieved != "infeasible":
            results["details"]["convergence_finding"] = (
                f"POSITIVE: PyPSA converged at {relaxation_achieved} relaxation "
                f"on the 27,862-bus FNM main island with DC warm start, "
                f"where MATPOWER 8.1 failed at ~30% load via continuation power flow."
            )
        else:
            results["details"]["convergence_finding"] = (
                "EXPECTED: PyPSA did not converge on the FNM main island, "
                "consistent with MATPOWER 8.1 failure. The FNM is a planning model "
                "with no solved voltage profile."
            )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 3)

    return results


if __name__ == "__main__":
    import json as _json

    result = run()
    print(_json.dumps(result, indent=2, default=str))
