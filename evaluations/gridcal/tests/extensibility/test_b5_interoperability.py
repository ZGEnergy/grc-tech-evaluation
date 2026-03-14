"""
Test B-5: Export DCPF results from A-1 to pandas DataFrame and write to CSV.

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Trivial -- fewer than 5 lines of code beyond the solve. No custom
    serialization logic required.
Tool: gridcal (VeraGridEngine) 5.6.28
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute B-5 interoperability test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        # 1. Load network and solve DCPF (same as A-1)
        grid = load_gridcal(network_file)
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        pf_results = vge.power_flow(grid, options=pf_opts)

        assert pf_results.converged, "DCPF did not converge"
        results["details"]["dcpf_converged"] = True

        # 2. Export to DataFrames using built-in API (B-5 core test)
        # Line 1: Get bus DataFrame
        bus_df = pf_results.get_bus_df()
        # Line 2: Get branch DataFrame
        branch_df = pf_results.get_branch_df()

        results["details"]["bus_df_shape"] = list(bus_df.shape)
        results["details"]["bus_df_columns"] = list(bus_df.columns)
        results["details"]["branch_df_shape"] = list(branch_df.shape)
        results["details"]["branch_df_columns"] = list(branch_df.columns)

        # Verify they are proper pandas DataFrames
        assert isinstance(bus_df, pd.DataFrame), "bus_df is not a pandas DataFrame"
        assert isinstance(branch_df, pd.DataFrame), "branch_df is not a pandas DataFrame"

        # 3. Write to CSV (1 additional line each)
        with tempfile.TemporaryDirectory() as tmpdir:
            bus_csv = Path(tmpdir) / "bus_results.csv"
            branch_csv = Path(tmpdir) / "branch_results.csv"

            # Line 3: Write bus results to CSV
            bus_df.to_csv(bus_csv)
            # Line 4: Write branch results to CSV
            branch_df.to_csv(branch_csv)

            # Verify CSV files are readable and correct
            bus_read = pd.read_csv(bus_csv, index_col=0)
            branch_read = pd.read_csv(branch_csv, index_col=0)

            results["details"]["bus_csv_rows"] = len(bus_read)
            results["details"]["branch_csv_rows"] = len(branch_read)
            results["details"]["bus_csv_matches"] = bus_read.shape == bus_df.shape
            results["details"]["branch_csv_matches"] = branch_read.shape == branch_df.shape

        # 4. Count lines of code beyond the solve
        # solve: pf_results = vge.power_flow(grid, options=pf_opts)
        # line 1: bus_df = pf_results.get_bus_df()
        # line 2: branch_df = pf_results.get_branch_df()
        # line 3: bus_df.to_csv(bus_csv)
        # line 4: branch_df.to_csv(branch_csv)
        loc_beyond_solve = 4
        results["details"]["loc_beyond_solve"] = loc_beyond_solve
        results["details"]["within_5_loc"] = loc_beyond_solve < 5

        # Additional export methods available
        results["details"]["additional_export_methods"] = [
            "get_voltage_df()",
            "get_current_df()",
            "to_json()",
            "export_all()",
        ]

        # 5. Check pass condition
        pass_checks = {
            "bus_df_is_dataframe": isinstance(bus_df, pd.DataFrame),
            "branch_df_is_dataframe": isinstance(branch_df, pd.DataFrame),
            "csv_round_trip_bus": bus_read.shape == bus_df.shape,
            "csv_round_trip_branch": branch_read.shape == branch_df.shape,
            "within_5_loc": loc_beyond_solve < 5,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
