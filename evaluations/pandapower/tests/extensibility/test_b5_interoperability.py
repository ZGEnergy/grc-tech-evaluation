"""
Test B-5: Export DCPF results to DataFrame and CSV

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Trivial -- fewer than 5 lines of code beyond the solve. No
    custom serialization logic required.
Tool: pandapower 3.4.0

Note: pandapower results ARE DataFrames natively (net.res_bus, net.res_line),
so export should be trivial.
Depends on: A-1
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute DCPF result export test."""
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
        import pandas as pd

        # 1. Load and solve DCPF (same as A-1)
        net = load_pandapower(network_file)
        pp.rundcpp(net)

        if not net.converged:
            results["errors"].append("DCPF did not converge")
            return results

        # 2. Extract results as DataFrames (already native)
        res_bus = net.res_bus
        res_line = net.res_line
        res_gen = net.res_gen
        res_ext_grid = net.res_ext_grid
        res_trafo = net.res_trafo

        results["details"]["res_bus_type"] = type(res_bus).__name__
        results["details"]["res_line_type"] = type(res_line).__name__
        results["details"]["res_bus_shape"] = list(res_bus.shape)
        results["details"]["res_line_shape"] = list(res_line.shape)
        results["details"]["res_gen_shape"] = list(res_gen.shape)
        results["details"]["res_ext_grid_shape"] = list(res_ext_grid.shape)
        results["details"]["res_trafo_shape"] = list(res_trafo.shape)

        # Verify these are genuine pandas DataFrames
        assert isinstance(res_bus, pd.DataFrame), "res_bus is not a DataFrame"
        assert isinstance(res_line, pd.DataFrame), "res_line is not a DataFrame"

        # 3. Export to CSV (trivial: one line per table)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Line 1: bus results to CSV
            res_bus.to_csv(tmppath / "res_bus.csv")
            # Line 2: line results to CSV
            res_line.to_csv(tmppath / "res_line.csv")
            # Line 3: generator results to CSV
            res_gen.to_csv(tmppath / "res_gen.csv")
            # Line 4: ext_grid results to CSV
            res_ext_grid.to_csv(tmppath / "res_ext_grid.csv")

            # Verify the CSVs are valid by reading them back
            bus_back = pd.read_csv(tmppath / "res_bus.csv", index_col=0)
            line_back = pd.read_csv(tmppath / "res_line.csv", index_col=0)

            results["details"]["csv_bus_shape"] = list(bus_back.shape)
            results["details"]["csv_line_shape"] = list(line_back.shape)
            results["details"]["csv_bus_columns"] = list(bus_back.columns)
            results["details"]["csv_line_columns"] = list(line_back.columns)

            # Verify roundtrip fidelity
            bus_match = bus_back.shape == res_bus.shape
            line_match = line_back.shape == res_line.shape
            results["details"]["csv_roundtrip_bus_shape_match"] = bus_match
            results["details"]["csv_roundtrip_line_shape_match"] = line_match

            # Check file sizes
            results["details"]["csv_file_sizes_bytes"] = {
                "res_bus.csv": (tmppath / "res_bus.csv").stat().st_size,
                "res_line.csv": (tmppath / "res_line.csv").stat().st_size,
                "res_gen.csv": (tmppath / "res_gen.csv").stat().st_size,
                "res_ext_grid.csv": (tmppath / "res_ext_grid.csv").stat().st_size,
            }

        # 4. Count lines of export code
        # The export is exactly 4 lines: one .to_csv() call per result table.
        # No custom serialization logic. No data transformation.
        export_loc = 4
        results["details"]["export_lines_of_code"] = export_loc
        results["details"]["custom_serialization_needed"] = False

        # 5. Document the API
        results["details"]["export_api"] = (
            "net.res_bus is a pandas DataFrame; export is just "
            "net.res_bus.to_csv('path.csv'). Same for res_line, res_gen, "
            "res_ext_grid, res_trafo. Zero custom serialization."
        )

        # 6. Show sample data
        results["details"]["sample_bus_data"] = res_bus.head(5).to_dict()
        results["details"]["sample_line_data"] = res_line.head(5).to_dict()

        # Pass condition: fewer than 5 lines, no custom serialization
        if export_loc < 5 and bus_match and line_match:
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
