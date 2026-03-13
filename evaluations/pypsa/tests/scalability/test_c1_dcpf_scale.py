"""
Test C-1: DCPF Scale (dcpf_scale)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: Wall-clock time and peak memory recorded.
Tool: PyPSA 1.1.2
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc -> pypsa."""
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
    """Execute DC Power Flow on ACTIVSg10k (10000-bus). Run 3 times, report median.

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
        "workarounds": [
            "Used matpowercaseframes.CaseFrames to parse .m -> pypower ppc -> pypsa "
            "(no native MATPOWER reader in PyPSA)",
            "overwrite_zero_s_nom=1.0 applied to fix 2462 zero-rated lines in ACTIVSg10k",
        ],
    }

    start = time.perf_counter()
    try:
        # 1. Load network (load once, copy for repeated solves)
        load_start = time.perf_counter()
        n_base = load_network(network_file)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n_base.buses)
        results["details"]["n_lines"] = len(n_base.lines)
        results["details"]["n_transformers"] = len(n_base.transformers)
        results["details"]["n_generators"] = len(n_base.generators)
        results["details"]["n_loads"] = len(n_base.loads)
        results["details"]["load_seconds"] = load_elapsed
        print(
            f"Network loaded: {len(n_base.buses)} buses, {len(n_base.lines)} lines, "
            f"{len(n_base.generators)} generators in {load_elapsed:.2f}s"
        )

        # 2. Run n.lpf() 3 times and record timing; report median
        N_RUNS = 3
        run_times = []
        peak_mems = []
        first_result = None

        for run_i in range(N_RUNS):
            n = n_base.copy()  # fresh copy for each run

            tracemalloc.start()
            t0 = time.perf_counter()
            n.lpf()
            t1 = time.perf_counter()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            elapsed = t1 - t0
            run_times.append(elapsed)
            peak_mems.append(peak / (1024 * 1024))
            print(f"  Run {run_i + 1}: {elapsed:.3f}s, peak_mem={peak / (1024 * 1024):.1f} MB")

            if run_i == 0:
                first_result = n

        median_time = float(np.median(run_times))
        results["details"]["run_times_seconds"] = run_times
        results["details"]["median_solve_seconds"] = median_time
        results["details"]["min_solve_seconds"] = float(min(run_times))
        results["details"]["max_solve_seconds"] = float(max(run_times))
        results["details"]["peak_memory_mb"] = float(np.median(peak_mems))
        print(f"\nMedian solve time: {median_time:.3f}s (3 runs: {run_times})")
        print(f"Peak memory (median): {float(np.median(peak_mems)):.1f} MB")

        # 3. Validate nontrivial solution from first run
        n = first_result
        v_ang_vals = n.buses_t.v_ang.iloc[0]
        p0_vals = n.lines_t.p0.iloc[0]
        slack_buses = n.buses[n.buses.control == "Slack"].index
        non_slack_angles = v_ang_vals.drop(slack_buses, errors="ignore")
        n_nonzero_non_slack = int((non_slack_angles.abs() > 1e-9).sum())
        n_nonzero_flows = int((p0_vals.abs() > 1e-9).sum())

        assert n_nonzero_non_slack > 0, (
            f"All non-slack bus angles are zero — DCPF may not have solved. "
            f"n_nonzero_non_slack={n_nonzero_non_slack}"
        )
        assert n_nonzero_flows > 0, "All line flows are zero — DCPF did not solve"

        results["details"]["n_nonzero_non_slack_angles"] = n_nonzero_non_slack
        results["details"]["n_nonzero_flows"] = n_nonzero_flows
        results["details"]["max_v_ang_deg"] = float(v_ang_vals.abs().max() * 180 / np.pi)
        results["details"]["max_line_flow_mw"] = float(p0_vals.abs().max())
        results["details"]["total_load_mw"] = float(n_base.loads.p_set.sum())

        print("\n=== Validation ===")
        print(f"  Non-zero angles: {n_nonzero_non_slack}/{len(n_base.buses)} buses")
        print(f"  Non-zero flows:  {n_nonzero_flows}/{len(n_base.lines)} lines")
        print(f"  Max angle: {results['details']['max_v_ang_deg']:.3f} deg")
        print(f"  Max flow: {results['details']['max_line_flow_mw']:.1f} MW")

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
