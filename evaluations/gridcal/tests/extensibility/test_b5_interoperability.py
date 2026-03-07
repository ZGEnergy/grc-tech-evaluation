"""B-5: Interoperability — export DCPF results to pandas DataFrame and CSV on IEEE 39-bus (TINY).

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Trivial (fewer than 5 lines beyond the solve). No custom serialization.
Depends on: A-1 (DCPF).
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Execute B-5 interoperability test."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import pandas as pd
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # ── Step 1: Run DCPF ──
        grid = vge.open_file(NETWORK_FILE)
        opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)

        t0 = time.perf_counter()
        results = vge.power_flow(grid, options=opts)
        t_pf = time.perf_counter() - t0

        if not results.converged:
            errors.append("DCPF did not converge")
            return {
                "status": "fail",
                "wall_clock_seconds": t_pf,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        details["dcpf_converged"] = True

        # ── Step 2: Export to pandas DataFrame ──
        t0 = time.perf_counter()
        bus_df = results.get_bus_df()
        branch_df = results.get_branch_df()
        t_export = time.perf_counter() - t0

        details["bus_df_type"] = type(bus_df).__name__
        details["bus_df_shape"] = list(bus_df.shape)
        details["bus_df_columns"] = list(bus_df.columns)
        details["bus_df_index_name"] = bus_df.index.name
        details["bus_df_sample"] = bus_df.head(3).to_dict()

        details["branch_df_type"] = type(branch_df).__name__
        details["branch_df_shape"] = list(branch_df.shape)
        details["branch_df_columns"] = list(branch_df.columns)
        details["branch_df_sample"] = branch_df.head(3).to_dict()

        details["export_to_df_seconds"] = round(t_export, 6)
        details["lines_for_df_export"] = 2  # bus_df = ...; branch_df = ...

        # ── Step 3: Write to CSV ──
        with tempfile.TemporaryDirectory() as tmpdir:
            bus_csv = Path(tmpdir) / "bus_results.csv"
            branch_csv = Path(tmpdir) / "branch_results.csv"

            t0 = time.perf_counter()
            bus_df.to_csv(bus_csv)
            branch_df.to_csv(branch_csv)
            t_csv = time.perf_counter() - t0

            # Verify CSV roundtrip
            bus_read = pd.read_csv(bus_csv, index_col=0)
            branch_read = pd.read_csv(branch_csv, index_col=0)

            details["csv_write_seconds"] = round(t_csv, 6)
            details["bus_csv_size_bytes"] = bus_csv.stat().st_size
            details["branch_csv_size_bytes"] = branch_csv.stat().st_size
            details["bus_csv_roundtrip_shape"] = list(bus_read.shape)
            details["branch_csv_roundtrip_shape"] = list(branch_read.shape)
            details["lines_for_csv_export"] = 2  # bus_df.to_csv(...); branch_df.to_csv(...)

        # ── Step 4: Verify DataFrame is standard pandas ──
        is_pandas_bus = isinstance(bus_df, pd.DataFrame)
        is_pandas_branch = isinstance(branch_df, pd.DataFrame)
        details["is_standard_pandas"] = is_pandas_bus and is_pandas_branch

        # Total lines beyond the solve
        total_export_lines = 4  # get_bus_df, get_branch_df, to_csv x2
        details["total_lines_beyond_solve"] = total_export_lines
        details["custom_serialization_needed"] = False

        wall_clock = t_pf + t_export + t_csv
        details["wall_clock_seconds"] = round(wall_clock, 6)

        # ── Assessment ──
        if is_pandas_bus and is_pandas_branch and total_export_lines <= 5:
            status = "pass"
            details["pass_rationale"] = (
                f"DCPF results exported to pandas DataFrames via get_bus_df() and get_branch_df() "
                f"({total_export_lines} lines total). Standard pandas to_csv() for file output. "
                "No custom serialization required."
            )
        else:
            status = "fail"
            if not is_pandas_bus or not is_pandas_branch:
                errors.append("Result DataFrames are not standard pandas")
            if total_export_lines > 5:
                errors.append(f"Export requires {total_export_lines} lines (limit is 5)")

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
