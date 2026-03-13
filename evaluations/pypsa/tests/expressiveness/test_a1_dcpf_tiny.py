"""
Test A-1: DC Power Flow (dcpf)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Converges. Nodal injections, line flows, and voltage angles accessible
  as structured output (DataFrame, dict, or named array — not raw solver vector).
Tool: PyPSA 1.1.2
"""

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

# Repo root is 4 levels up: tests/expressiveness/ -> tests/ -> pypsa/ -> evaluations/ -> root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")


def load_network(network_file: str):
    """Load case39.m via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    # PyPSA's import_from_pypower_ppc expects numpy arrays, not DataFrames
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
    """Execute DC Power Flow on IEEE 39-bus network.

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
        # 1. Load network
        n = load_network(network_file)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)

        results["workarounds"].append(
            "Used matpowercaseframes.CaseFrames to parse .m -> pypower ppc -> pypsa "
            "(no native MATPOWER reader in PyPSA)"
        )

        # 2. Run DC (linear) power flow
        solve_start = time.perf_counter()
        n.lpf()
        solve_elapsed = time.perf_counter() - solve_start
        results["details"]["solve_seconds"] = solve_elapsed

        # 3. Extract structured outputs

        # Voltage angles (radians)
        v_ang = n.buses_t.v_ang
        # Nodal injections (MW) - computed from line flows
        p_inject = n.buses_t.p
        # Line active power flows (MW)
        p0 = n.lines_t.p0

        # Check outputs are DataFrames
        assert isinstance(v_ang, pd.DataFrame), "v_ang should be DataFrame"
        assert isinstance(p_inject, pd.DataFrame), "p_inject should be DataFrame"
        assert isinstance(p0, pd.DataFrame), "p0 should be DataFrame"

        # Validate: v_ang has at least one nonzero bus angle (not trivial solution)
        v_ang_vals = v_ang.iloc[0]
        n_nonzero_angles = (v_ang_vals.abs() > 1e-9).sum()
        n_buses = len(n.buses)

        # At minimum, non-slack buses should have nonzero angles
        slack_buses = n.buses[n.buses.control == "Slack"].index
        non_slack_angles = v_ang_vals.drop(slack_buses, errors="ignore")
        n_nonzero_non_slack = (non_slack_angles.abs() > 1e-9).sum()

        assert n_nonzero_non_slack > 0, (
            f"All non-slack bus angles are zero — DCPF may not have solved. "
            f"n_nonzero={n_nonzero_angles}, n_buses={n_buses}"
        )

        # Check line flows are nonzero
        p0_vals = p0.iloc[0]
        n_nonzero_flows = (p0_vals.abs() > 1e-9).sum()
        assert n_nonzero_flows > 0, "All line flows are zero — DCPF did not solve"

        # 4. Collect structured results
        results["details"]["v_ang_deg_first5"] = (v_ang_vals.head(5) * 180 / np.pi).to_dict()
        results["details"]["p0_mw_first5"] = p0_vals.head(5).to_dict()
        results["details"]["p_inject_first5"] = p_inject.iloc[0].head(5).to_dict()
        results["details"]["n_nonzero_angles"] = int(n_nonzero_angles)
        results["details"]["n_nonzero_flows"] = int(n_nonzero_flows)
        results["details"]["max_v_ang_deg"] = float(v_ang_vals.abs().max() * 180 / np.pi)
        results["details"]["max_line_flow_mw"] = float(p0_vals.abs().max())
        results["details"]["total_generation_mw"] = float(n.generators.p_nom.sum())
        results["details"]["slack_buses"] = list(slack_buses)
        results["details"]["output_types"] = {
            "v_ang": str(type(v_ang)),
            "p_inject": str(type(p_inject)),
            "p0": str(type(p0)),
        }

        # Print first 5 rows of each output for verification
        print("=== Voltage Angles (radians) — first 5 buses ===")
        print(v_ang_vals.head(5).to_string())
        print("\n=== Line Flows p0 (MW) — first 5 lines ===")
        print(p0_vals.head(5).to_string())
        print("\n=== Nodal Injections p (MW) — first 5 buses ===")
        print(p_inject.iloc[0].head(5).to_string())

        # 5. Pass condition check
        # All three outputs accessible as DataFrames AND nontrivial values
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
