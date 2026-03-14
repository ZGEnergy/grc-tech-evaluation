"""
Test A-1: Solve DCPF

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Converges. Nodal injections, line flows, and voltage angles
    accessible as structured output (DataFrame, dict, or named array — not raw
    solver vector).
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

# Add shared loader to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute DCPF test and return structured results."""
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

        # 1. Load network
        net = load_pandapower(network_file)

        bus_count = len(net.bus)
        line_count = len(net.line)
        trafo_count = len(net.trafo)
        gen_count = len(net.gen)
        ext_grid_count = len(net.ext_grid)

        results["details"]["bus_count"] = bus_count
        results["details"]["line_count"] = line_count
        results["details"]["trafo_count"] = trafo_count
        results["details"]["gen_count"] = gen_count
        results["details"]["ext_grid_count"] = ext_grid_count

        # 2. Run DCPF
        solve_start = time.perf_counter()
        pp.rundcpp(net)
        solve_time = time.perf_counter() - solve_start
        results["details"]["solve_seconds"] = solve_time

        # 3. Check convergence
        converged = net.converged
        results["details"]["converged"] = converged
        if not converged:
            results["errors"].append("DCPF did not converge")
            return results

        # 4. Extract structured results

        # Bus results: voltage angles (DCPF sets all Vm=1.0 by definition)
        res_bus = net.res_bus
        results["details"]["res_bus_columns"] = list(res_bus.columns)
        results["details"]["res_bus_shape"] = list(res_bus.shape)
        results["details"]["voltage_angles_deg"] = res_bus["va_degree"].to_dict()
        results["details"]["bus_p_mw"] = res_bus["p_mw"].to_dict()

        # Verify voltage angles are not all zero (non-trivial solution)
        va = res_bus["va_degree"]
        nonzero_angles = (va.abs() > 1e-6).sum()
        results["details"]["nonzero_angle_buses"] = int(nonzero_angles)

        # Line results: P flows
        res_line = net.res_line
        results["details"]["res_line_columns"] = list(res_line.columns)
        results["details"]["res_line_shape"] = list(res_line.shape)
        results["details"]["line_p_from_mw_sample"] = res_line["p_from_mw"].head(10).to_dict()
        results["details"]["line_p_to_mw_sample"] = res_line["p_to_mw"].head(10).to_dict()

        # Trafo results
        if len(net.res_trafo) > 0:
            res_trafo = net.res_trafo
            results["details"]["res_trafo_columns"] = list(res_trafo.columns)
            results["details"]["res_trafo_shape"] = list(res_trafo.shape)

        # Generator results
        res_gen = net.res_gen
        results["details"]["gen_p_mw"] = res_gen["p_mw"].to_dict()

        # Ext grid results (slack)
        res_ext_grid = net.res_ext_grid
        results["details"]["ext_grid_p_mw"] = res_ext_grid["p_mw"].to_dict()

        # 5. Verify pass conditions
        # - Converges: checked above
        # - Nodal injections accessible: res_bus.p_mw is a DataFrame column
        # - Line flows accessible: res_line.p_from_mw is a DataFrame column
        # - Voltage angles accessible: res_bus.va_degree is a DataFrame column
        # All are pandas DataFrames — structured output
        results["details"]["output_format"] = "pandas.DataFrame"

        if nonzero_angles < 2:
            results["errors"].append(
                f"Only {nonzero_angles} buses have nonzero voltage angles "
                f"(expected most of {bus_count} to be nonzero)"
            )
            return results

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
