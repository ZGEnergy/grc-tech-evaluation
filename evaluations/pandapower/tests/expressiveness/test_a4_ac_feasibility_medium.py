"""
Test A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch

Dimension: expressiveness
Network: MEDIUM (ACTIVSg10k ~10000 buses)
Pass condition: Achievable within the same model context (no export to file and reimport).
    Voltage violations and thermal limit violations identifiable from results.
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute AC feasibility test on DC OPF dispatch and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen)

        # 2. Solve DC OPF to get dispatch
        pp.rundcopp(net)
        if not net["OPF_converged"]:
            results["errors"].append("DC OPF did not converge")
            return results

        results["details"]["dcopf_converged"] = True
        results["details"]["dcopf_objective"] = float(net.res_cost)

        # 3. Extract DC OPF dispatch
        dcopf_gen_dispatch = net.res_gen["p_mw"].copy()
        dcopf_ext_grid_dispatch = net.res_ext_grid["p_mw"].copy()

        # 4. Fix generator active power to DC OPF dispatch values
        for idx in net.gen.index:
            net.gen.at[idx, "p_mw"] = dcopf_gen_dispatch[idx]

        # 5. Run ACPF within the same model context
        acpf_start = time.perf_counter()
        acpf_converged = False

        # Try flat start
        try:
            pp.runpp(net, init="flat", max_iteration=100)
            acpf_converged = net["converged"]
            results["details"]["acpf_init"] = "flat"
        except Exception:
            pass

        if not acpf_converged:
            # DC warm start fallback
            try:
                pp.rundcpp(net)
                pp.runpp(net, init="dc", max_iteration=200)
                acpf_converged = net["converged"]
                results["details"]["acpf_init"] = "dc_warm_start"
            except Exception:
                pass

        if not acpf_converged:
            # Relaxed tolerance
            try:
                pp.runpp(net, init="dc", max_iteration=300, tolerance_mva=1e-4)
                acpf_converged = net["converged"]
                results["details"]["acpf_init"] = "dc_warm_start_relaxed_tol"
            except Exception:
                pass

        acpf_elapsed = time.perf_counter() - acpf_start
        results["details"]["acpf_converged"] = acpf_converged
        results["details"]["acpf_wall_clock_seconds"] = acpf_elapsed

        if not acpf_converged:
            results["errors"].append("ACPF did not converge with any initialization")
            # Still document same-model-context capability
            results["details"]["same_model_context"] = True
            results["details"]["context_note"] = (
                "DC OPF dispatch was applied in-place. ACPF attempted on same net object."
            )
            return results

        # 6. Verify same model context
        results["details"]["same_model_context"] = True
        results["details"]["context_note"] = (
            "DC OPF dispatch applied to generator p_mw in-place, "
            "then ACPF run on same net object. No file export/reimport."
        )

        # 7. Check voltage violations
        vm_pu = net.res_bus["vm_pu"]
        v_min, v_max = 0.95, 1.05
        voltage_violations = vm_pu[(vm_pu < v_min) | (vm_pu > v_max)]
        results["details"]["voltage_range"] = {
            "min": float(vm_pu.min()),
            "max": float(vm_pu.max()),
            "mean": float(vm_pu.mean()),
        }
        results["details"]["voltage_violations_count"] = len(voltage_violations)

        # 8. Check thermal/line loading violations
        loading = net.res_line["loading_percent"]
        thermal_violations = loading[loading > 100.0]
        results["details"]["line_loading_range"] = {
            "min": float(loading.min()),
            "max": float(loading.max()),
            "mean": float(loading.mean()),
        }
        results["details"]["thermal_violations_count"] = len(thermal_violations)

        # Trafo loading
        if len(net.trafo) > 0 and len(net.res_trafo) > 0:
            trafo_loading = net.res_trafo["loading_percent"]
            trafo_violations = trafo_loading[trafo_loading > 100.0]
            results["details"]["trafo_loading_range"] = {
                "min": float(trafo_loading.min()),
                "max": float(trafo_loading.max()),
                "mean": float(trafo_loading.mean()),
            }
            results["details"]["trafo_violations_count"] = len(trafo_violations)

        # 9. Reactive power
        if "q_mvar" in net.res_gen.columns:
            q_gen = net.res_gen["q_mvar"]
            results["details"]["reactive_power_range"] = {
                "min": float(q_gen.min()),
                "max": float(q_gen.max()),
            }

        # 10. Slack bus comparison
        acpf_ext_grid = net.res_ext_grid["p_mw"].copy()
        results["details"]["ext_grid_power_difference_mw"] = float(
            acpf_ext_grid.sum() - dcopf_ext_grid_dispatch.sum()
        )

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
