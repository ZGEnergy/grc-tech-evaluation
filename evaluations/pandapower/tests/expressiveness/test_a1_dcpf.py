"""
Test A-1: Solve DCPF

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Converges. Nodal injections, line flows, and voltage angles accessible
    as structured output (DataFrame, dict, or named array - not raw solver vector).
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute DCPF test and return structured results."""
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
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["ext_grid_count"] = len(net.ext_grid)

        # 2. Solve DCPF (timed)
        start = time.perf_counter()
        pp.rundcpp(net)
        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed

        # 3. Verify convergence
        if not net["converged"]:
            results["errors"].append("DCPF did not converge")
            return results

        # 4. Extract structured results
        # Voltage angles (DataFrame)
        va = net.res_bus[["va_degree"]].copy()
        results["details"]["output_format"] = "pandas.DataFrame"
        results["details"]["voltage_angles_sample"] = va.head(5).to_dict()

        # Line flows (DataFrame)
        line_flows = net.res_line[["p_from_mw", "p_to_mw"]].copy()
        results["details"]["line_flows_sample"] = line_flows.head(5).to_dict()

        # Nodal injections from res_bus
        bus_p = net.res_bus[["p_mw"]].copy()
        results["details"]["nodal_injections_sample"] = bus_p.head(5).to_dict()

        # Summary statistics
        results["details"]["total_buses"] = len(net.res_bus)
        results["details"]["total_lines_with_results"] = len(net.res_line)
        results["details"]["max_angle_deg"] = float(va["va_degree"].max())
        results["details"]["min_angle_deg"] = float(va["va_degree"].min())
        results["details"]["max_line_flow_mw"] = float(line_flows["p_from_mw"].abs().max())

        # 5. Check pass condition - structured output accessible
        assert len(net.res_bus) > 0, "No bus results"
        assert len(net.res_line) > 0, "No line results"
        assert "va_degree" in net.res_bus.columns, "No voltage angle column"
        assert "p_from_mw" in net.res_line.columns, "No line flow column"
        assert "p_mw" in net.res_bus.columns, "No nodal injection column"

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
