"""
Test A-1: DC Power Flow (dcpf)

Dimension: expressiveness
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m, ~10000 buses)
Pass condition: Same as TINY + record wall-clock time and peak memory.
  Focus: timing (primary grade metric for MEDIUM).
Tool: PyPSA 1.1.2
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc dict -> pypsa.

    Uses overwrite_zero_s_nom=1.0 to handle the 2462 zero-rated lines in
    ACTIVSg10k (zero s_nom causes OPF infeasibility; for DCPF it forces
    capacity check to use 1 MVA which is fine).
    """
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
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute DC Power Flow on ACTIVSg10k (10000-bus) network.

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
            "(no native MATPOWER reader in PyPSA)"
        ],
    }

    start = time.perf_counter()
    try:
        # 1. Load network (timed separately from solve)
        load_start = time.perf_counter()
        n = load_network(network_file)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["n_loads"] = len(n.loads)
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["base_mva"] = (
            float(n.meta.get("baseMVA", 100.0)) if hasattr(n, "meta") else 100.0
        )

        print(
            f"Network loaded: {len(n.buses)} buses, {len(n.lines)} lines, "
            f"{len(n.transformers)} transformers, {len(n.generators)} generators"
        )
        print(f"Load time: {load_elapsed:.3f}s")

        # 2. Run DC (linear) power flow with peak memory tracking
        tracemalloc.start()
        solve_start = time.perf_counter()
        n.lpf()
        solve_elapsed = time.perf_counter() - solve_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak_mem / (1024 * 1024)
        print(f"DCPF solve time: {solve_elapsed:.3f}s")
        print(f"Peak memory: {peak_mem / (1024 * 1024):.1f} MB")

        # 3. Extract structured outputs
        v_ang = n.buses_t.v_ang
        p_inject = n.buses_t.p
        p0_lines = n.lines_t.p0
        _p0_xfmr = n.transformers_t.p0

        assert isinstance(v_ang, pd.DataFrame), "v_ang should be DataFrame"
        assert isinstance(p_inject, pd.DataFrame), "p_inject should be DataFrame"
        assert isinstance(p0_lines, pd.DataFrame), "p0_lines should be DataFrame"

        # 4. Validate nontrivial solution
        v_ang_vals = v_ang.iloc[0]
        slack_buses = n.buses[n.buses.control == "Slack"].index
        non_slack_angles = v_ang_vals.drop(slack_buses, errors="ignore")
        n_nonzero_angles = int((v_ang_vals.abs() > 1e-9).sum())
        n_nonzero_non_slack = int((non_slack_angles.abs() > 1e-9).sum())

        assert n_nonzero_non_slack > 0, (
            f"All non-slack bus angles are zero — DCPF may not have solved. "
            f"n_nonzero={n_nonzero_angles}, n_buses={len(n.buses)}"
        )

        p0_vals = p0_lines.iloc[0]
        n_nonzero_flows = int((p0_vals.abs() > 1e-9).sum())
        assert n_nonzero_flows > 0, "All line flows are zero — DCPF did not solve"

        # 5. Collect structured results
        results["details"]["n_nonzero_angles"] = n_nonzero_angles
        results["details"]["n_nonzero_non_slack_angles"] = n_nonzero_non_slack
        results["details"]["n_nonzero_flows"] = n_nonzero_flows
        results["details"]["max_v_ang_deg"] = float(v_ang_vals.abs().max() * 180 / np.pi)
        results["details"]["max_line_flow_mw"] = float(p0_vals.abs().max())
        results["details"]["total_load_mw"] = float(n.loads.p_set.sum())
        results["details"]["slack_buses"] = list(slack_buses)
        results["details"]["v_ang_deg_first5"] = (v_ang_vals.head(5) * 180 / np.pi).to_dict()
        results["details"]["p0_first5"] = p0_vals.head(5).to_dict()
        if len(p_inject) > 0:
            results["details"]["p_inject_first5"] = p_inject.iloc[0].head(5).to_dict()

        print("\n=== DCPF Results Summary ===")
        print(
            f"  Buses: {len(n.buses)}, Lines: {len(n.lines)}, Transformers: {len(n.transformers)}"
        )
        print(f"  Non-zero angles: {n_nonzero_angles}/{len(n.buses)} buses")
        print(f"  Non-zero flows: {n_nonzero_flows}/{len(n.lines)} lines")
        print(f"  Max angle: {results['details']['max_v_ang_deg']:.3f} deg")
        print(f"  Max flow: {results['details']['max_line_flow_mw']:.1f} MW")

        print("\n=== Voltage Angles (degrees) — first 5 buses ===")
        print((v_ang_vals.head(5) * 180 / np.pi).to_string())
        print("\n=== Line Flows p0 (MW) — first 5 lines ===")
        print(p0_vals.head(5).to_string())

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
