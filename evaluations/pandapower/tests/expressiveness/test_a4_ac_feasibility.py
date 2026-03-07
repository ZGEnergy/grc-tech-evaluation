"""
Test A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Achievable within the same model context (no export to file and reimport).
    Voltage violations and thermal limit violations identifiable from results.
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
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

        # 2. Solve DC OPF to get dispatch (same as A-3)
        pp.rundcopp(net)
        if not net["OPF_converged"]:
            results["errors"].append("DC OPF did not converge")
            return results

        results["details"]["dcopf_converged"] = True
        results["details"]["dcopf_objective"] = float(net.res_cost)

        # 3. Extract DC OPF dispatch
        dcopf_gen_dispatch = net.res_gen["p_mw"].copy()
        dcopf_ext_grid_dispatch = net.res_ext_grid["p_mw"].copy()
        results["details"]["dcopf_gen_dispatch_mw"] = dcopf_gen_dispatch.to_dict()
        results["details"]["dcopf_ext_grid_dispatch_mw"] = dcopf_ext_grid_dispatch.to_dict()

        # 4. Fix generator active power to DC OPF dispatch values
        # For gen elements: set p_mw to DC OPF result and mark as in_service
        for idx in net.gen.index:
            net.gen.at[idx, "p_mw"] = dcopf_gen_dispatch[idx]

        # For ext_grid: it acts as slack - cannot fix p_mw directly,
        # but we can convert it to a gen with fixed output if needed.
        # Actually in pandapower, ext_grid is the slack bus and will adjust
        # to balance power. We leave it as-is for ACPF.

        # 5. Run ACPF within the same model context (flat start)
        acpf_start = time.perf_counter()
        try:
            pp.runpp(net, init="flat", max_iteration=100)
            acpf_elapsed = time.perf_counter() - acpf_start
            results["details"]["acpf_converged"] = True
            results["details"]["acpf_wall_clock_seconds"] = acpf_elapsed
            results["details"]["acpf_init"] = "flat"
        except pp.powerflow.LoadflowNotConverged:
            acpf_elapsed = time.perf_counter() - acpf_start
            results["details"]["acpf_flat_start_failed"] = True
            # Try DC warm start fallback per convergence-protocol.md
            try:
                pp.runpp(net, init="dc", max_iteration=100)
                acpf_elapsed_dc = time.perf_counter() - acpf_start
                results["details"]["acpf_converged"] = True
                results["details"]["acpf_wall_clock_seconds"] = acpf_elapsed_dc
                results["details"]["acpf_init"] = "dc_warm_start"
                results["details"]["convergence_note"] = (
                    "Flat start failed; DC warm start succeeded"
                )
            except pp.powerflow.LoadflowNotConverged:
                results["details"]["acpf_converged"] = False
                results["errors"].append("ACPF did not converge with flat or DC warm start")
                return results

        # 6. Verify same model context (no export/reimport)
        results["details"]["same_model_context"] = True
        results["details"]["context_note"] = (
            "DC OPF dispatch was applied to generator p_mw in-place, "
            "then ACPF was run on the same net object. No file export/reimport."
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
        if len(voltage_violations) > 0:
            results["details"]["voltage_violations"] = {
                int(k): float(v) for k, v in voltage_violations.items()
            }

        # 8. Check thermal/line loading violations
        loading = net.res_line["loading_percent"]
        thermal_violations = loading[loading > 100.0]
        results["details"]["line_loading_range"] = {
            "min": float(loading.min()),
            "max": float(loading.max()),
            "mean": float(loading.mean()),
        }
        results["details"]["thermal_violations_count"] = len(thermal_violations)
        if len(thermal_violations) > 0:
            results["details"]["thermal_violations"] = {
                int(k): float(v) for k, v in thermal_violations.items()
            }

        # Also check trafo loading if present
        if len(net.trafo) > 0 and len(net.res_trafo) > 0:
            trafo_loading = net.res_trafo["loading_percent"]
            trafo_violations = trafo_loading[trafo_loading > 100.0]
            results["details"]["trafo_loading_range"] = {
                "min": float(trafo_loading.min()),
                "max": float(trafo_loading.max()),
                "mean": float(trafo_loading.mean()),
            }
            results["details"]["trafo_violations_count"] = len(trafo_violations)

        # 9. Check reactive power limits
        if "q_mvar" in net.res_gen.columns:
            q_gen = net.res_gen["q_mvar"]
            q_min = net.gen["min_q_mvar"] if "min_q_mvar" in net.gen.columns else None
            q_max = net.gen["max_q_mvar"] if "max_q_mvar" in net.gen.columns else None
            results["details"]["reactive_power_range"] = {
                "min": float(q_gen.min()),
                "max": float(q_gen.max()),
            }
            if q_min is not None and q_max is not None:
                q_violations = q_gen[(q_gen < q_min) | (q_gen > q_max)]
                results["details"]["reactive_power_violations_count"] = len(q_violations)

        # 10. Compare ext_grid power (slack bus active power in AC vs DC)
        acpf_ext_grid = net.res_ext_grid["p_mw"].copy()
        results["details"]["acpf_ext_grid_dispatch_mw"] = acpf_ext_grid.to_dict()
        results["details"]["ext_grid_power_difference_mw"] = float(
            acpf_ext_grid.sum() - dcopf_ext_grid_dispatch.sum()
        )
        results["details"]["ext_grid_difference_note"] = (
            "Difference reflects losses and reactive power adjustments in ACPF."
        )

        # Pass condition: achievable within same model context, violations identifiable
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
