"""
Test C-5: AC Feasibility — Progressive Relaxation (DCPF baseline, ACPF at 0%/10%/20% relaxation)

Dimension: scalability
Network: SMALL (ACTIVSg2000)
Pass condition: Diagnostic finding — all outcomes (0%, 10%, 20%, infeasible) produce informational data.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

# Voltage violation thresholds
VM_MIN = 0.95
VM_MAX = 1.05


def _collect_violations(net) -> dict:
    """Collect voltage, thermal, and reactive power violations from solved network."""
    violations: dict = {}

    # Voltage violations
    vm = net.res_bus["vm_pu"]
    v_low = vm[vm < VM_MIN]
    v_high = vm[vm > VM_MAX]
    violations["voltage"] = {
        "low_count": len(v_low),
        "high_count": len(v_high),
        "total_count": len(v_low) + len(v_high),
        "vm_min": float(vm.min()),
        "vm_max": float(vm.max()),
        "vm_mean": float(vm.mean()),
    }

    # Thermal violations (line loading > 100%)
    line_loading = net.res_line["loading_percent"]
    line_overload = line_loading[line_loading > 100.0]
    violations["thermal_line"] = {
        "count": len(line_overload),
        "max_loading_pct": float(line_loading.max()),
        "mean_loading_pct": float(line_loading.mean()),
    }

    # Transformer loading violations
    if len(net.res_trafo) > 0:
        trafo_loading = net.res_trafo["loading_percent"]
        trafo_overload = trafo_loading[trafo_loading > 100.0]
        violations["thermal_trafo"] = {
            "count": len(trafo_overload),
            "max_loading_pct": float(trafo_loading.max()),
        }

    # Total P losses
    total_p_loss = float(net.res_line["pl_mw"].sum())
    if len(net.res_trafo) > 0:
        total_p_loss += float(net.res_trafo["pl_mw"].sum())
    violations["total_p_loss_mw"] = total_p_loss

    return violations


def _try_acpf(net, init: str = "dc", max_iteration: int = 50) -> tuple[bool, float]:
    """Attempt ACPF and return (converged, solve_seconds)."""
    import pandapower as pp

    t0 = time.perf_counter()
    try:
        pp.runpp(
            net,
            algorithm="nr",
            init=init,
            calculate_voltage_angles=True,
            tolerance_mva=1e-8,
            max_iteration=max_iteration,
        )
        elapsed = time.perf_counter() - t0
        return bool(net.converged), elapsed
    except Exception:
        elapsed = time.perf_counter() - t0
        return False, elapsed


def _relax_thermal_limits(net, relaxation_pct: float) -> None:
    """Relax thermal limits by given percentage (0.10 = 10%)."""
    factor = 1.0 + relaxation_pct
    net.line["max_i_ka"] *= factor
    if len(net.trafo) > 0 and "sn_mva" in net.trafo.columns:
        net.trafo["sn_mva"] *= factor


def run(
    network_file: str = "data/networks/case_ACTIVSg2000.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute AC feasibility progressive relaxation test."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandapower as pp

        # =========================================================
        # STEP 1: Load network and run DCPF baseline
        # =========================================================
        net = load_pandapower(network_file)

        results["details"]["base_mva"] = float(net.sn_mva)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)

        tracemalloc.start()

        # DCPF baseline
        dcpf_start = time.perf_counter()
        pp.rundcpp(net)
        dcpf_time = time.perf_counter() - dcpf_start

        if not net.converged:
            results["errors"].append("DCPF did not converge on SMALL network")
            return results

        results["details"]["dcpf"] = {
            "converged": True,
            "wall_clock_seconds": dcpf_time,
            "total_gen_mw": float(net.res_gen["p_mw"].sum() + net.res_ext_grid["p_mw"].sum()),
            "max_line_loading_pct": float(net.res_line["loading_percent"].max()),
            "mean_line_loading_pct": float(net.res_line["loading_percent"].mean()),
        }

        # Save original thermal limits for relaxation steps
        original_line_max_i_ka = net.line["max_i_ka"].copy()
        original_trafo_sn_mva = None
        if len(net.trafo) > 0 and "sn_mva" in net.trafo.columns:
            original_trafo_sn_mva = net.trafo["sn_mva"].copy()

        # =========================================================
        # STEP 2: ACPF at 0% relaxation (DC warm start)
        # =========================================================
        converged_0, time_0 = _try_acpf(net, init="dc", max_iteration=50)

        step_0_result: dict = {
            "relaxation_pct": 0,
            "converged": converged_0,
            "wall_clock_seconds": time_0,
        }

        if converged_0:
            step_0_result["violations"] = _collect_violations(net)
            # Extract NR iterations if available
            if hasattr(net, "_ppc") and net._ppc is not None:
                iters = net._ppc.get("iterations", None)
                if iters is not None:
                    step_0_result["nr_iterations"] = int(iters)
        else:
            # Try flat start as fallback
            converged_0_flat, time_0_flat = _try_acpf(net, init="flat", max_iteration=50)
            step_0_result["flat_start_attempted"] = True
            step_0_result["flat_start_converged"] = converged_0_flat
            step_0_result["flat_start_seconds"] = time_0_flat
            if converged_0_flat:
                step_0_result["converged"] = True
                step_0_result["wall_clock_seconds"] = time_0 + time_0_flat
                step_0_result["violations"] = _collect_violations(net)

        results["details"]["acpf_0pct"] = step_0_result

        # Determine final relaxation level
        relaxation_level_achieved = None
        if step_0_result.get("converged"):
            relaxation_level_achieved = 0

        # =========================================================
        # STEP 3: ACPF at 10% relaxation (if 0% failed)
        # =========================================================
        if not step_0_result.get("converged"):
            # Reset thermal limits and apply 10% relaxation
            net.line["max_i_ka"] = original_line_max_i_ka.copy()
            if original_trafo_sn_mva is not None:
                net.trafo["sn_mva"] = original_trafo_sn_mva.copy()

            _relax_thermal_limits(net, 0.10)

            converged_10, time_10 = _try_acpf(net, init="dc", max_iteration=50)
            step_10_result: dict = {
                "relaxation_pct": 10,
                "converged": converged_10,
                "wall_clock_seconds": time_10,
            }
            if converged_10:
                step_10_result["violations"] = _collect_violations(net)
                relaxation_level_achieved = 10
            else:
                converged_10_flat, time_10_flat = _try_acpf(net, init="flat", max_iteration=50)
                step_10_result["flat_start_attempted"] = True
                step_10_result["flat_start_converged"] = converged_10_flat
                step_10_result["flat_start_seconds"] = time_10_flat
                if converged_10_flat:
                    step_10_result["converged"] = True
                    step_10_result["violations"] = _collect_violations(net)
                    relaxation_level_achieved = 10

            results["details"]["acpf_10pct"] = step_10_result

            # =========================================================
            # STEP 4: ACPF at 20% relaxation (if 10% also failed)
            # =========================================================
            if not step_10_result.get("converged"):
                net.line["max_i_ka"] = original_line_max_i_ka.copy()
                if original_trafo_sn_mva is not None:
                    net.trafo["sn_mva"] = original_trafo_sn_mva.copy()

                _relax_thermal_limits(net, 0.20)

                converged_20, time_20 = _try_acpf(net, init="dc", max_iteration=50)
                step_20_result: dict = {
                    "relaxation_pct": 20,
                    "converged": converged_20,
                    "wall_clock_seconds": time_20,
                }
                if converged_20:
                    step_20_result["violations"] = _collect_violations(net)
                    relaxation_level_achieved = 20
                else:
                    converged_20_flat, time_20_flat = _try_acpf(net, init="flat", max_iteration=50)
                    step_20_result["flat_start_attempted"] = True
                    step_20_result["flat_start_converged"] = converged_20_flat
                    step_20_result["flat_start_seconds"] = time_20_flat
                    if converged_20_flat:
                        step_20_result["converged"] = True
                        step_20_result["violations"] = _collect_violations(net)
                        relaxation_level_achieved = 20

                results["details"]["acpf_20pct"] = step_20_result

        # Peak memory
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)

        # Summary
        results["details"]["relaxation_level_achieved"] = relaxation_level_achieved

        # This is a diagnostic/informational test — all outcomes produce data
        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        try:
            tracemalloc.stop()
        except RuntimeError:
            pass
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
