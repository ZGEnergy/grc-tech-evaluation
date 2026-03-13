"""
Test B-5: Interoperability — DataFrame export

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: Trivial — fewer than 5 lines of code beyond the solve.
  Record shape of exported DataFrame and timing.
Tool: PyPSA 1.1.2
"""

import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")
OUTPUT_CSV = str(
    REPO_ROOT / "evaluations" / "pypsa" / "results" / "extensibility" / "b5_v_ang_export_medium.csv"
)


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=1.0)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DCPF on 10k-bus network and export voltage angles DataFrame to CSV.

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

        # 1. Load network
        print("Loading 10k network...")
        n = load_network(network_file)
        print(f"Loaded: {len(n.buses)} buses, {len(n.lines)} lines")
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)

        # 2. Run DCPF
        print("Running DCPF...")
        t_lpf_start = time.perf_counter()
        n.lpf()
        t_lpf_elapsed = time.perf_counter() - t_lpf_start
        print(f"DCPF done in {t_lpf_elapsed:.2f}s")
        results["details"]["lpf_seconds"] = t_lpf_elapsed

        # --- Lines beyond the solve (pass condition: < 5) ---
        # Line 1: access the result (already a DataFrame)
        v_ang_df = n.buses_t.v_ang  # line 1 beyond solve

        # Line 2: write to CSV
        output_path = OUTPUT_CSV
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        t_csv_start = time.perf_counter()
        v_ang_df.to_csv(output_path)  # line 2 beyond solve
        t_csv_elapsed = time.perf_counter() - t_csv_start

        loc_beyond_solve = 2

        print(f"DataFrame shape: {v_ang_df.shape}")
        print(f"CSV written in {t_csv_elapsed:.3f}s to: {output_path}")

        # 3. Verify output
        assert isinstance(v_ang_df, pd.DataFrame), "v_ang should be a DataFrame"
        assert v_ang_df.shape[1] == len(n.buses), (
            f"Expected {len(n.buses)} bus columns, got {v_ang_df.shape[1]}"
        )

        # Read back CSV to confirm it is a proper labeled CSV
        # Note: for 10k buses the CSV is large; verify subset
        csv_back = pd.read_csv(output_path, index_col=0)
        assert csv_back.shape[1] == len(n.buses), "CSV columns do not match bus count"

        # Spot-check voltage angles (first 10 buses)
        orig_vals = v_ang_df.iloc[0, :10].values
        csv_vals = csv_back.iloc[0, :10].values
        max_diff = float(np.abs(orig_vals - csv_vals).max())

        # Check that angles are non-trivial (not all zero)
        all_zero = (np.abs(v_ang_df.values) < 1e-12).all()
        n_nonzero = int((np.abs(v_ang_df.values) > 1e-6).sum())
        v_ang_max = float(np.abs(v_ang_df.values).max())

        print(f"Non-zero angle entries: {n_nonzero}/{v_ang_df.size}")
        print(f"Max |voltage angle| (rad): {v_ang_max:.6f}")
        print(f"CSV round-trip max error (first 10 buses): {max_diff:.2e}")
        print(f"Lines of code beyond solve: {loc_beyond_solve}")

        results["details"]["df_shape"] = list(v_ang_df.shape)
        results["details"]["n_buses_in_df"] = int(v_ang_df.shape[1])
        results["details"]["csv_path"] = output_path
        results["details"]["csv_roundtrip_max_diff_first10"] = max_diff
        results["details"]["loc_beyond_solve"] = loc_beyond_solve
        results["details"]["csv_write_seconds"] = t_csv_elapsed
        results["details"]["n_nonzero_angles"] = n_nonzero
        results["details"]["v_ang_max_rad"] = v_ang_max
        results["details"]["v_ang_first5_rad"] = v_ang_df.iloc[0].head(5).to_dict()

        errors = []
        if loc_beyond_solve >= 5:
            errors.append(f"Too many lines beyond solve: {loc_beyond_solve} (pass condition: < 5)")
        if all_zero:
            errors.append("All voltage angles are zero — DCPF may not have solved")
        if max_diff > 1e-9:
            errors.append(f"CSV round-trip error too large: {max_diff:.2e}")

        results["errors"].extend(errors)
        if not errors:
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
