"""
Test B-5: Export DCPF results from A-1 to pandas DataFrame and write to CSV.

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Trivial -- fewer than 5 lines of code beyond the solve.
Tool: pandapower v3.4.0

APPROACH: pandapower stores all results in pandas DataFrames natively
(net.res_bus, net.res_line, etc.). Export is simply .to_csv().
"""

import json
import os
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute interoperability export test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network and solve DCPF (reproducing A-1)
        net = from_mpc(network_file, f_hz=60)
        pp.rundcpp(net)
        assert net["converged"], "DCPF did not converge"

        # 2. Export results to CSV -- this is the core of the test
        # pandapower results are ALREADY pandas DataFrames, so export is trivial
        output_dir = "evaluations/pandapower/results/extensibility"
        os.makedirs(output_dir, exist_ok=True)

        bus_csv = os.path.join(output_dir, "B-5_dcpf_bus_results.csv")
        line_csv = os.path.join(output_dir, "B-5_dcpf_line_results.csv")

        # --- The actual export: 2 lines of code beyond the solve ---
        net.res_bus.to_csv(bus_csv)
        net.res_line.to_csv(line_csv)

        # 3. Verify the CSVs were written and are readable
        import pandas as pd

        bus_df = pd.read_csv(bus_csv, index_col=0)
        line_df = pd.read_csv(line_csv, index_col=0)

        results["details"]["bus_csv_path"] = bus_csv
        results["details"]["line_csv_path"] = line_csv
        results["details"]["bus_csv_rows"] = len(bus_df)
        results["details"]["bus_csv_columns"] = list(bus_df.columns)
        results["details"]["line_csv_rows"] = len(line_df)
        results["details"]["line_csv_columns"] = list(line_df.columns)

        # Verify round-trip: data matches
        assert len(bus_df) == len(net.res_bus), "Bus CSV row count mismatch"
        assert len(line_df) == len(net.res_line), "Line CSV row count mismatch"

        # Show the export is truly minimal
        results["details"]["export_code"] = (
            'net.res_bus.to_csv("bus_results.csv")\nnet.res_line.to_csv("line_results.csv")'
        )
        results["details"]["lines_of_code_for_export"] = 2
        results["details"]["output_format"] = "pandas.DataFrame -> CSV"

        # Also demonstrate other trivial exports
        results["details"]["other_trivial_exports"] = {
            "to_json": "net.res_bus.to_json()",
            "to_excel": "net.res_bus.to_excel('results.xlsx')",
            "to_parquet": "net.res_bus.to_parquet('results.parquet')",
            "to_dict": "net.res_bus.to_dict()",
            "to_numpy": "net.res_bus.values",
        }

        # Sample of exported data
        results["details"]["bus_sample"] = bus_df.head(5).to_dict()
        results["details"]["line_sample"] = line_df.head(5).to_dict()

        # 4. Clean up CSV files
        os.remove(bus_csv)
        os.remove(line_csv)
        results["details"]["csv_files_cleaned_up"] = True

        # 5. Pass -- trivially achieved
        results["status"] = "pass"
        results["details"]["method"] = (
            "pandapower stores all results as pandas DataFrames natively. "
            "Export to CSV is a single .to_csv() call per result table. "
            "No conversion, no intermediate format, no workarounds. "
            "2 lines of code total for bus + line results."
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
