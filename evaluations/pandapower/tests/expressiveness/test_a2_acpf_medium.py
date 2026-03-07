"""
Test A-2: Solve ACPF (Newton-Raphson)

Dimension: expressiveness
Network: MEDIUM (ACTIVSg10k ~10000 buses)
Pass condition: Converges. Bus voltage magnitudes and angles, line P/Q flows, and losses
    accessible as structured output.
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute ACPF test on MEDIUM network and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    try:
        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)

        # 2. Attempt flat start (convergence protocol: flat start first)
        start = time.perf_counter()
        try:
            pp.runpp(net, algorithm="nr", init="flat", max_iteration=100)
            flat_start_converged = net["converged"]
        except Exception as e:
            flat_start_converged = False
            results["details"]["flat_start_error"] = str(e)

        elapsed_flat = time.perf_counter() - start
        results["details"]["flat_start_converged"] = flat_start_converged
        results["details"]["flat_start_wall_clock"] = elapsed_flat

        if not flat_start_converged:
            # DC warm start fallback per convergence-protocol.md
            results["details"]["dc_warm_start_attempted"] = True
            pp.rundcpp(net)

            start = time.perf_counter()
            try:
                pp.runpp(net, algorithm="nr", init="dc", max_iteration=200)
                dc_warm_converged = net["converged"]
            except Exception as e:
                dc_warm_converged = False
                results["details"]["dc_warm_start_error"] = str(e)

            elapsed_dc = time.perf_counter() - start
            results["details"]["dc_warm_start_wall_clock"] = elapsed_dc

            if not dc_warm_converged:
                # Try relaxed tolerance
                results["details"]["relaxed_tolerance_attempted"] = True
                start = time.perf_counter()
                try:
                    pp.runpp(net, algorithm="nr", init="dc", max_iteration=300, tolerance_mva=1e-4)
                    relaxed_converged = net["converged"]
                except Exception as e:
                    relaxed_converged = False
                    results["details"]["relaxed_tolerance_error"] = str(e)

                elapsed_relaxed = time.perf_counter() - start
                results["details"]["relaxed_tolerance_wall_clock"] = elapsed_relaxed

                if not relaxed_converged:
                    results["errors"].append(
                        "ACPF did not converge with flat start, DC warm start, or relaxed tolerance"
                    )
                    return results
                else:
                    results["wall_clock_seconds"] = elapsed_relaxed
                    results["details"]["convergence_note"] = "Required relaxed tolerance (1e-4)"
            else:
                results["wall_clock_seconds"] = elapsed_dc
                results["details"]["convergence_note"] = "DC warm start required"
        else:
            results["details"]["dc_warm_start_attempted"] = False
            results["wall_clock_seconds"] = elapsed_flat

        # 3. Extract structured results
        results["details"]["output_format"] = "pandas.DataFrame"

        bus_results = net.res_bus[["vm_pu", "va_degree", "p_mw", "q_mvar"]].copy()
        results["details"]["bus_results_sample"] = bus_results.head(5).to_dict()
        results["details"]["total_buses"] = len(net.res_bus)

        line_cols = ["p_from_mw", "q_from_mvar", "p_to_mw", "q_to_mvar", "pl_mw", "ql_mvar"]
        available_cols = [c for c in line_cols if c in net.res_line.columns]
        line_results = net.res_line[available_cols].copy()
        results["details"]["line_results_sample"] = line_results.head(5).to_dict()
        results["details"]["total_lines_with_results"] = len(net.res_line)

        if "pl_mw" in net.res_line.columns:
            total_p_loss = float(net.res_line["pl_mw"].sum())
            results["details"]["total_p_loss_mw"] = total_p_loss
        if "ql_mvar" in net.res_line.columns:
            total_q_loss = float(net.res_line["ql_mvar"].sum())
            results["details"]["total_q_loss_mvar"] = total_q_loss

        if len(net.trafo) > 0 and len(net.res_trafo) > 0:
            if "pl_mw" in net.res_trafo.columns:
                results["details"]["total_trafo_p_loss_mw"] = float(net.res_trafo["pl_mw"].sum())

        results["details"]["vm_max_pu"] = float(bus_results["vm_pu"].max())
        results["details"]["vm_min_pu"] = float(bus_results["vm_pu"].min())
        results["details"]["va_max_deg"] = float(bus_results["va_degree"].max())
        results["details"]["va_min_deg"] = float(bus_results["va_degree"].min())

        # 4. Check pass condition
        assert len(net.res_bus) > 0, "No bus results"
        assert "vm_pu" in net.res_bus.columns, "No voltage magnitude column"
        assert "va_degree" in net.res_bus.columns, "No voltage angle column"
        assert len(net.res_line) > 0, "No line results"

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
