"""
Test B-5: Interoperability

Dimension: extensibility
Network: TINY (case39)
Pass condition: Trivial -- fewer than 5 lines of code beyond the solve. No custom serialization logic required.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import os
import tempfile
import time
import traceback

import pypsa
from matpowercaseframes import CaseFrames


def _load_network(case_path: str) -> pypsa.Network:
    """Load MATPOWER .m file into PyPSA Network."""
    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    try:
        ppc["gencost"] = cf.gencost.values
    except Exception:
        pass
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    return n


def run(network_file: str = "/workspace/data/networks/case39.m") -> dict:
    """Execute the test and return structured results.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandas as pd

        # 1. Load network
        n = _load_network(network_file)

        # 2. Run DCPF (this is the A-1 solve)
        n.lpf()

        # 3. Extract results to pandas DataFrames (already native pandas)
        bus_results = n.buses_t.v_ang.copy()  # voltage angles
        line_flows = n.lines_t.p0.copy()  # line flows (from-end)

        # Also get static results
        bus_static = n.buses[["v_nom"]].copy()
        bus_static["v_ang_rad"] = n.buses_t.v_ang.iloc[0] if len(n.buses_t.v_ang) > 0 else 0.0

        results["details"]["bus_results_type"] = type(bus_results).__name__
        results["details"]["line_flows_type"] = type(line_flows).__name__
        results["details"]["bus_results_shape"] = list(bus_results.shape)
        results["details"]["line_flows_shape"] = list(line_flows.shape)

        # 4. Write to CSV (the interoperability test)
        with tempfile.TemporaryDirectory() as tmpdir:
            bus_csv = os.path.join(tmpdir, "bus_angles.csv")
            flows_csv = os.path.join(tmpdir, "line_flows.csv")

            bus_results.to_csv(bus_csv)  # 1 line
            line_flows.to_csv(flows_csv)  # 1 line

            # Verify files exist and are readable
            bus_df_reload = pd.read_csv(bus_csv, index_col=0)
            flows_df_reload = pd.read_csv(flows_csv, index_col=0)

            results["details"]["bus_csv_rows"] = len(bus_df_reload)
            results["details"]["bus_csv_cols"] = len(bus_df_reload.columns)
            results["details"]["flows_csv_rows"] = len(flows_df_reload)
            results["details"]["flows_csv_cols"] = len(flows_df_reload.columns)

            # Show sample data
            results["details"]["bus_angle_sample"] = {
                str(k): round(float(v), 6) for k, v in list(bus_results.iloc[0].items())[:5]
            }
            results["details"]["line_flow_sample"] = {
                str(k): round(float(v), 4) for k, v in list(line_flows.iloc[0].items())[:5]
            }

        # Lines of code for export: 2 lines (one per .to_csv call)
        # Results are already pandas DataFrames, no conversion needed
        results["details"]["loc"] = 2
        results["details"]["export_notes"] = (
            "Results are natively pandas DataFrames. Export is trivial: "
            "df.to_csv(path). No custom serialization required."
        )

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
