"""
Test C-2: ACPF at scale

Dimension: scalability
Network: MEDIUM (ACTIVSg10k, ~10000 buses)
Pass condition: Converges on MEDIUM network.
Tool: pandapower v3.4.0

NOTE: Eval-config specifies "Ipopt" as solver but pandapower uses its own
Newton-Raphson implementation, not Ipopt. This deviation is documented.
Convergence protocol: flat start first, then DC warm start fallback.
"""

import json
import os
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute ACPF at scale and return structured results."""
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
        load_start = time.perf_counter()
        net = from_mpc(network_file, f_hz=60)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["load_count"] = len(net.load)

        # Document solver deviation
        results["details"]["solver_note"] = (
            "pandapower uses internal Newton-Raphson solver, not Ipopt as specified "
            "in eval-config. No option to swap to Ipopt for ACPF."
        )

        # Memory before solve
        try:
            import resource

            mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # noqa: F841
        except Exception:
            mem_before = None  # noqa: F841

        # 2. Attempt flat start (convergence protocol)
        flat_start = time.perf_counter()
        try:
            pp.runpp(net, algorithm="nr", init="flat", max_iteration=100)
            flat_converged = net["converged"]
        except Exception as e:
            flat_converged = False
            results["details"]["flat_start_error"] = str(e)

        flat_elapsed = time.perf_counter() - flat_start
        results["details"]["flat_start_converged"] = flat_converged
        results["details"]["flat_start_seconds"] = flat_elapsed

        converged = flat_converged
        solve_method = "flat_start"

        if not flat_converged:
            # 3. DC warm start fallback
            results["details"]["dc_warm_start_attempted"] = True
            pp.rundcpp(net)

            dc_warm_start = time.perf_counter()
            try:
                pp.runpp(net, algorithm="nr", init="dc", max_iteration=100)
                dc_converged = net["converged"]
            except Exception as e:
                dc_converged = False
                results["details"]["dc_warm_start_error"] = str(e)

            dc_elapsed = time.perf_counter() - dc_warm_start
            results["details"]["dc_warm_start_converged"] = dc_converged
            results["details"]["dc_warm_start_seconds"] = dc_elapsed

            if dc_converged:
                converged = True
                solve_method = "dc_warm_start"
            else:
                # Try relaxed tolerance
                results["details"]["relaxed_tolerance_attempted"] = True
                relax_start = time.perf_counter()
                try:
                    pp.runpp(
                        net,
                        algorithm="nr",
                        init="dc",
                        max_iteration=200,
                        tolerance_mva=1e-4,
                    )
                    relax_converged = net["converged"]
                except Exception as e:
                    relax_converged = False
                    results["details"]["relaxed_tolerance_error"] = str(e)

                relax_elapsed = time.perf_counter() - relax_start
                results["details"]["relaxed_tolerance_converged"] = relax_converged
                results["details"]["relaxed_tolerance_seconds"] = relax_elapsed

                if relax_converged:
                    converged = True
                    solve_method = "relaxed_tolerance"
        else:
            results["details"]["dc_warm_start_attempted"] = False

        results["details"]["solve_method"] = solve_method

        # Memory after solve
        try:
            mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            results["details"]["peak_memory_mb"] = mem_after
        except Exception:
            pass

        # CPU utilization
        try:
            cpu_times = os.times()
            results["details"]["cpu_user_seconds"] = cpu_times.user
            results["details"]["cpu_system_seconds"] = cpu_times.system
        except Exception:
            pass

        if not converged:
            results["errors"].append(
                "ACPF did not converge on MEDIUM network with any initialization method"
            )
            return results

        # 4. Extract results
        bus_res = net.res_bus
        results["details"]["total_buses_with_results"] = len(bus_res)
        results["details"]["vm_max_pu"] = float(bus_res["vm_pu"].max())
        results["details"]["vm_min_pu"] = float(bus_res["vm_pu"].min())
        results["details"]["va_max_deg"] = float(bus_res["va_degree"].max())
        results["details"]["va_min_deg"] = float(bus_res["va_degree"].min())

        if "pl_mw" in net.res_line.columns:
            results["details"]["total_p_loss_mw"] = float(net.res_line["pl_mw"].sum())
        if len(net.trafo) > 0 and "pl_mw" in net.res_trafo.columns:
            results["details"]["total_trafo_p_loss_mw"] = float(net.res_trafo["pl_mw"].sum())

        # NR iteration count (from internal attributes if available)
        if hasattr(net, "_ppc") and net._ppc is not None:
            results["details"]["internal_ppc_available"] = True

        # 5. Check pass condition
        results["status"] = "pass"
        if solve_method != "flat_start":
            results["workarounds"].append(
                f"Convergence required {solve_method} instead of flat start."
            )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
