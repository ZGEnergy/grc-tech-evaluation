"""
Test B-5: Export DCPF results from A-1 to pandas DataFrame and write to CSV

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Trivial — fewer than 5 lines of code beyond the solve. No custom
  serialization logic required.
Tool: PyPSA 1.1.2
"""

import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
OUTPUT_CSV = str(
    REPO_ROOT / "evaluations" / "pypsa" / "results" / "extensibility" / "b5_v_ang_export.csv"
)


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DCPF and export voltage angles DataFrame to CSV.

    The export is trivial: n.buses_t.v_ang is already a pandas DataFrame.
    Only 2 lines of code beyond the solve call are required:
      1. v_ang_df = n.buses_t.v_ang
      2. v_ang_df.to_csv(path)

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import numpy as np
        import pandas as pd
        from matpower_loader import load_pypsa

        # 1. Load network and run DCPF (replicating A-1)
        n = load_pypsa(network_file)
        n.lpf()  # DC power flow solve

        # --- Lines beyond the solve (pass condition: < 5) ---
        # Line 1: access the result (already a pandas DataFrame)
        v_ang_df = n.buses_t.v_ang  # line 1

        # Line 2: write to CSV
        Path(OUTPUT_CSV).parent.mkdir(parents=True, exist_ok=True)
        v_ang_df.to_csv(OUTPUT_CSV)  # line 2

        loc_beyond_solve = 2

        # Also export line flows to demonstrate generality
        p0_df = n.lines_t.p0  # line flows — also already a DataFrame
        p0_csv = OUTPUT_CSV.replace("v_ang_export", "p0_export")
        p0_df.to_csv(p0_csv)

        # 2. Verify outputs
        assert isinstance(v_ang_df, pd.DataFrame), "v_ang should be a DataFrame"
        assert isinstance(p0_df, pd.DataFrame), "p0 should be a DataFrame"
        assert v_ang_df.shape[1] == len(n.buses), (
            f"Expected {len(n.buses)} bus columns, got {v_ang_df.shape[1]}"
        )

        # Read back CSV to confirm round-trip fidelity
        csv_back = pd.read_csv(OUTPUT_CSV, index_col=0)
        assert csv_back.shape[1] == len(n.buses), "CSV columns do not match bus count"
        assert list(csv_back.columns) == list(n.buses.index), (
            "CSV column names do not match bus names"
        )

        # Check voltage angle values are preserved
        orig_vals = v_ang_df.values
        csv_vals = csv_back.values
        max_diff = float(np.abs(orig_vals - csv_vals).max())
        assert max_diff < 1e-9, f"CSV round-trip error: max_diff={max_diff}"

        # Verify non-trivial solution
        n_nonzero = int((np.abs(v_ang_df.values) > 1e-9).sum())
        v_ang_max = float(np.abs(v_ang_df.values).max())

        results["details"]["output_types"] = {
            "v_ang": str(type(v_ang_df)),
            "p0": str(type(p0_df)),
        }
        results["details"]["df_shape"] = list(v_ang_df.shape)
        results["details"]["n_buses"] = int(v_ang_df.shape[1])
        results["details"]["n_lines"] = int(p0_df.shape[1])
        results["details"]["csv_path_v_ang"] = OUTPUT_CSV
        results["details"]["csv_path_p0"] = p0_csv
        results["details"]["csv_columns_verified"] = True
        results["details"]["csv_roundtrip_max_diff"] = max_diff
        results["details"]["loc_beyond_solve"] = loc_beyond_solve
        results["details"]["n_nonzero_angles"] = n_nonzero
        results["details"]["v_ang_max_rad"] = v_ang_max
        results["details"]["v_ang_first5_rad"] = v_ang_df.iloc[0].head(5).to_dict()
        results["details"]["p0_first5_mw"] = p0_df.iloc[0].head(5).to_dict()

        print(f"v_ang DataFrame shape: {v_ang_df.shape}")
        print(f"p0 DataFrame shape: {p0_df.shape}")
        print(f"CSV written to: {OUTPUT_CSV}")
        print(f"Lines of code beyond solve: {loc_beyond_solve}")
        print(f"CSV round-trip max error: {max_diff:.2e}")
        print(f"Non-zero angle entries: {n_nonzero}/{v_ang_df.size}")
        print(f"Max |voltage angle| (rad): {v_ang_max:.6f}")
        print("\nFirst 5 voltage angles (rad):")
        print(v_ang_df.iloc[0].head(5).to_string())
        print("\nFirst 5 line flows (MW):")
        print(p0_df.iloc[0].head(5).to_string())

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
