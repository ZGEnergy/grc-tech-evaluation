"""
Test B-5: Export DCPF results to pandas DataFrame and write to CSV.

Dimension: extensibility
Network: MEDIUM (ACTIVSg10k ~10000 buses)
Pass condition: Trivial -- fewer than 5 lines of code beyond the solve.
Tool: pandapower v3.4.0
"""

import json
import os
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute interoperability export test on MEDIUM."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load and solve DCPF
        net = from_mpc(network_file, f_hz=60)
        pp.rundcpp(net)
        assert net["converged"], "DCPF did not converge"

        results["details"]["bus_count"] = len(net.res_bus)
        results["details"]["line_count"] = len(net.res_line)

        # 2. Export to CSV
        output_dir = "/tmp/pandapower_b5_medium"
        os.makedirs(output_dir, exist_ok=True)

        bus_csv = os.path.join(output_dir, "dcpf_bus_results.csv")
        line_csv = os.path.join(output_dir, "dcpf_line_results.csv")

        net.res_bus.to_csv(bus_csv)
        net.res_line.to_csv(line_csv)

        # 3. Verify round-trip
        import pandas as pd

        bus_df = pd.read_csv(bus_csv, index_col=0)
        line_df = pd.read_csv(line_csv, index_col=0)

        results["details"]["bus_csv_rows"] = len(bus_df)
        results["details"]["bus_csv_columns"] = list(bus_df.columns)
        results["details"]["line_csv_rows"] = len(line_df)
        results["details"]["line_csv_columns"] = list(line_df.columns)

        assert len(bus_df) == len(net.res_bus), "Bus CSV row count mismatch"
        assert len(line_df) == len(net.res_line), "Line CSV row count mismatch"

        # File sizes
        results["details"]["bus_csv_size_kb"] = round(os.path.getsize(bus_csv) / 1024, 1)
        results["details"]["line_csv_size_kb"] = round(os.path.getsize(line_csv) / 1024, 1)

        results["details"]["lines_of_code_for_export"] = 2
        results["details"]["output_format"] = "pandas.DataFrame -> CSV"

        # Clean up
        os.remove(bus_csv)
        os.remove(line_csv)
        os.rmdir(output_dir)

        results["status"] = "pass"
        results["details"]["method"] = (
            "pandapower results are pandas DataFrames natively. "
            "Export is a single .to_csv() call per table. 2 lines of code."
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
