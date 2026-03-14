"""
Test A-11: Solve DC OPF on TINY with distributed slack (load-proportional).

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Tool supports distributed slack formulation. LMPs differ from single-slack
    results. Distributed slack weights are settable via API.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS

GridCal has `distributed_slack=True` in PowerFlowOptions but this only affects power flow
(DCPF/ACPF), not the OPF formulation. The linear OPF uses a PTDF-based formulation that
hardcodes `distributed_slack=False` in its internal LinearAnalysis call. There is no API
to set distributed slack weights in the OPF context.

This test documents that GridCal does not support distributed slack in DC OPF.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal

COST_MAP = {
    "hydro": {"c1": 5.0, "c2": 0.005},
    "nuclear": {"c1": 10.0, "c2": 0.010},
    "coal_large": {"c1": 25.0, "c2": 0.025},
    "gas_CC": {"c1": 40.0, "c2": 0.040},
}

BRANCH_DERATING = 0.70


def _setup_grid(network_file, timeseries_dir):
    """Load grid, apply differentiated costs and 70% branch derating."""
    grid = load_gridcal(network_file)
    generators = grid.get_generators()
    branches = grid.get_branches()

    ts_dir = Path(timeseries_dir) if timeseries_dir else None
    if ts_dir and (ts_dir / "gen_temporal_params.csv").exists():
        with open(ts_dir / "gen_temporal_params.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                idx = int(row["gen_index"])
                if idx < len(generators):
                    tech_key = row["tech_class_key"]
                    if tech_key in COST_MAP:
                        generators[idx].Cost = COST_MAP[tech_key]["c1"]
                        generators[idx].Cost2 = COST_MAP[tech_key]["c2"]
                        generators[idx].Cost0 = 0.0

    for branch in branches:
        if hasattr(branch, "rate") and branch.rate > 0:
            branch.rate = branch.rate * BRANCH_DERATING

    return grid


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute A-11 distributed slack OPF test."""
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
        from VeraGridEngine.enumerations import MIPSolvers, SolverType

        # =====================================================================
        # Step 1: Run single-slack DCOPF (baseline, same as A-3)
        # =====================================================================
        grid_single = _setup_grid(network_file, timeseries_dir)
        opf_opts = vge.OptimalPowerFlowOptions(
            solver=SolverType.LINEAR_OPF,
            mip_solver=MIPSolvers.HIGHS,
        )
        # Ensure embedded PF options have distributed_slack=False (default)
        opf_opts.power_flow_options.distributed_slack = False

        res_single = vge.linear_opf(grid_single, opf_opts)
        if not res_single.converged:
            results["errors"].append("Single-slack DCOPF did not converge")
            return results

        single_gen = res_single.generator_power.copy()
        single_lmps = res_single.bus_shadow_prices.copy()

        results["details"]["single_slack_total_gen_mw"] = float(np.sum(single_gen))
        results["details"]["single_slack_lmp_range"] = {
            "min": float(np.min(single_lmps)),
            "max": float(np.max(single_lmps)),
        }

        # =====================================================================
        # Step 2: Attempt distributed slack DCOPF
        # =====================================================================
        grid_dist = _setup_grid(network_file, timeseries_dir)
        opf_opts_dist = vge.OptimalPowerFlowOptions(
            solver=SolverType.LINEAR_OPF,
            mip_solver=MIPSolvers.HIGHS,
        )
        # Set distributed slack in the embedded power flow options
        opf_opts_dist.power_flow_options.distributed_slack = True

        res_dist = vge.linear_opf(grid_dist, opf_opts_dist)

        if not res_dist.converged:
            results["errors"].append("Distributed-slack DCOPF did not converge")
            return results

        dist_gen = res_dist.generator_power.copy()
        dist_lmps = res_dist.bus_shadow_prices.copy()

        results["details"]["dist_slack_total_gen_mw"] = float(np.sum(dist_gen))
        results["details"]["dist_slack_lmp_range"] = {
            "min": float(np.min(dist_lmps)),
            "max": float(np.max(dist_lmps)),
        }

        # Compare results
        gen_diff = float(np.max(np.abs(dist_gen - single_gen)))
        lmp_diff = float(np.max(np.abs(dist_lmps - single_lmps)))
        results["details"]["max_gen_diff_mw"] = gen_diff
        results["details"]["max_lmp_diff"] = lmp_diff
        results["details"]["results_differ"] = gen_diff > 0.01 or lmp_diff > 0.01

        # =====================================================================
        # Step 3: Check if distributed_slack option has any effect on OPF
        # =====================================================================
        # The linear OPF formulation (linear_opf_ts.py line 3022) hardcodes
        # distributed_slack=False in its internal LinearAnalysis call.
        # The power_flow_options.distributed_slack flag is not used by the OPF.

        results["details"]["analysis"] = (
            "The PowerFlowOptions.distributed_slack flag exists but is not used by the "
            "linear OPF formulation. The OPF formulation (linear_opf_ts.py) hardcodes "
            "distributed_slack=False in its PTDF computation via LinearAnalysis. "
            "Setting power_flow_options.distributed_slack=True has no effect on OPF "
            "dispatch or LMPs. The distributed_slack feature only applies to power flow "
            "(DCPF/ACPF), not to optimal power flow."
        )

        # Check for distributed slack weight API
        results["details"]["weight_api_available"] = False
        results["details"]["weight_api_note"] = (
            "No API found for setting distributed slack weights. The distributed slack "
            "in DCPF uses load-proportional distribution (hardcoded in LinearAnalysis), "
            "but this is not accessible or configurable in the OPF context."
        )

        # =====================================================================
        # Step 4: Demonstrate distributed slack works in DCPF (not OPF)
        # =====================================================================
        grid_pf1 = _setup_grid(network_file, timeseries_dir)
        pf_single = vge.power_flow(
            grid_pf1, vge.PowerFlowOptions(solver_type=SolverType.Linear, distributed_slack=False)
        )
        grid_pf2 = _setup_grid(network_file, timeseries_dir)
        pf_dist = vge.power_flow(
            grid_pf2, vge.PowerFlowOptions(solver_type=SolverType.Linear, distributed_slack=True)
        )

        pf_angle_diff = float(
            np.max(np.abs(np.angle(pf_single.voltage) - np.angle(pf_dist.voltage)))
        )
        results["details"]["dcpf_distributed_slack_works"] = pf_angle_diff > 0.01
        results["details"]["dcpf_max_angle_diff_rad"] = pf_angle_diff

        # =====================================================================
        # Pass/fail assessment
        # =====================================================================
        # The test requires distributed slack in DC OPF with settable weights.
        # GridCal does not support this — distributed_slack only applies to PF.

        pass_checks = {
            "distributed_slack_in_opf": False,  # not supported
            "lmps_differ": lmp_diff > 0.01,
            "weights_settable": False,  # no API
        }
        results["details"]["pass_checks"] = pass_checks

        results["status"] = "fail"
        results["errors"].append(
            "GridCal does not support distributed slack in DC OPF. The "
            "distributed_slack option only affects power flow (DCPF/ACPF). "
            "The linear OPF formulation hardcodes distributed_slack=False."
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
