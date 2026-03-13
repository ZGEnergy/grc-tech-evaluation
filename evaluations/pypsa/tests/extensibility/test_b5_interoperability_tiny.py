"""
Test B-5: Interoperability — DataFrame export

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Trivial — fewer than 5 lines of code beyond the solve.
Tool: PyPSA 1.1.2

Note: After n.lpf(), n.buses_t.v_ang is already a pandas DataFrame.
Export to CSV requires a single .to_csv() call — 1 line beyond the solve.
"""

import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
OUTPUT_CSV = str(
    REPO_ROOT / "evaluations" / "pypsa" / "results" / "extensibility" / "b5_v_ang_export.csv"
)


def load_network(network_file: str):
    """Load case39.m via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DCPF and export voltage angles DataFrame to CSV.

    The export is trivial: n.buses_t.v_ang is already a pandas DataFrame.
    Only 1 line of code beyond the solve call is required.

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
        import pandas as pd

        # 1. Load network and run DCPF (replicating A-1)
        n = load_network(network_file)
        n.lpf()  # DC power flow solve

        # --- Lines beyond the solve (pass condition: < 5) ---
        # Line 1: access the result (already a DataFrame)
        v_ang_df = n.buses_t.v_ang  # line 1 beyond solve

        # Line 2: write to CSV
        output_path = OUTPUT_CSV
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        v_ang_df.to_csv(output_path)  # line 2 beyond solve

        # Total lines beyond solve: 2 (access + csv write)
        loc_beyond_solve = 2

        # 2. Verify output
        assert isinstance(v_ang_df, pd.DataFrame), "v_ang should be a DataFrame"
        assert v_ang_df.shape[1] == len(n.buses), (
            f"Expected {len(n.buses)} bus columns, got {v_ang_df.shape[1]}"
        )

        # Read back CSV to confirm it is a proper labeled CSV
        csv_back = pd.read_csv(output_path, index_col=0)
        assert csv_back.shape[1] == len(n.buses), "CSV columns do not match bus count"
        assert list(csv_back.columns) == list(n.buses.index), (
            "CSV column names do not match bus names"
        )

        # Check that voltage angle values are preserved
        import numpy as np

        orig_vals = v_ang_df.values
        csv_vals = csv_back.values
        max_diff = float(np.abs(orig_vals - csv_vals).max())
        assert max_diff < 1e-9, f"CSV round-trip error: max_diff={max_diff}"

        results["details"]["output_type"] = str(type(v_ang_df))
        results["details"]["df_shape"] = list(v_ang_df.shape)
        results["details"]["n_buses"] = int(v_ang_df.shape[1])
        results["details"]["csv_path"] = output_path
        results["details"]["csv_columns_verified"] = True
        results["details"]["csv_roundtrip_max_diff"] = max_diff
        results["details"]["loc_beyond_solve"] = loc_beyond_solve
        results["details"]["v_ang_first5_rad"] = v_ang_df.iloc[0].head(5).to_dict()

        print(f"DataFrame shape: {v_ang_df.shape}")
        print(f"CSV written to: {output_path}")
        print(f"Lines of code beyond solve: {loc_beyond_solve}")
        print(f"CSV round-trip max error: {max_diff:.2e}")
        print("First 5 voltage angles (rad):")
        print(v_ang_df.iloc[0].head(5).to_string())

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
