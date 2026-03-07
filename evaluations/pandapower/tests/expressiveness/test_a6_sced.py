"""
Test A-6: Fix commitment schedule from A-5, solve economic dispatch as LP/QP

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Solves. Dispatch schedule extractable. UC and ED are cleanly separable
    as a two-stage workflow. Ramp rate constraints are demonstrably enforced between
    consecutive dispatch intervals in the ED stage.
Tool: pandapower v3.4.0

CRITICAL NOTE: A-5 (SCUC) FAILED. pandapower has no unit commitment formulation,
no MILP optimization, and no temporal constraints. Therefore A-6 also FAILS --
there is no commitment schedule to fix. This script documents the dependency failure
and demonstrates what pandapower CAN do: single-period economic dispatch via rundcopp().
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Attempt SCED test and document dependency failure on A-5."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["ext_grid_count"] = len(net.ext_grid)

        # 2. Document dependency failure
        results["details"]["dependency_failure"] = {
            "depends_on": "A-5 (SCUC)",
            "a5_status": "FAIL",
            "reason": (
                "pandapower has no SCUC capability. Without a commitment schedule "
                "from A-5, there is no commitment to fix for the ED stage. "
                "The two-stage UC/ED workflow is not achievable."
            ),
        }

        # 3. Document what SCED requires vs what pandapower provides
        results["details"]["sced_capability_assessment"] = {
            "fixed_commitment_from_scuc": False,
            "multi_period_economic_dispatch": False,
            "ramp_rate_constraints_between_intervals": False,
            "temporal_linking_constraints": False,
            "lp_qp_dispatch_formulation": False,
            "two_stage_uc_ed_separation": False,
        }

        results["details"]["what_pandapower_can_do"] = {
            "single_period_dcopf": True,
            "generator_dispatch_optimization": True,
            "lmp_extraction": True,
            "description": (
                "pandapower can solve single-period DC OPF via rundcopp(), "
                "which is economic dispatch for one snapshot. But it cannot: "
                "(1) accept a fixed commitment schedule, (2) enforce ramp rates "
                "between intervals, or (3) solve multi-period ED."
            ),
        }

        # 4. Demonstrate single-period ED (closest capability)
        pp.rundcopp(net)
        if net["OPF_converged"]:
            results["details"]["single_period_ed_converged"] = True
            results["details"]["single_period_objective"] = float(net.res_cost)
            results["details"]["gen_dispatch_mw"] = net.res_gen["p_mw"].to_dict()
            results["details"]["ext_grid_dispatch_mw"] = net.res_ext_grid["p_mw"].to_dict()

            # Show LMPs if available
            if "lam_p" in net.res_bus.columns:
                results["details"]["lmp_mean"] = float(net.res_bus["lam_p"].mean())
                results["details"]["lmp_range"] = [
                    float(net.res_bus["lam_p"].min()),
                    float(net.res_bus["lam_p"].max()),
                ]
        else:
            results["details"]["single_period_ed_converged"] = False

        # 5. Explicit failure
        results["status"] = "fail"
        results["errors"].append(
            "A-6 FAILS due to dependency on A-5 (SCUC), which FAILED. "
            "pandapower has no SCUC, so there is no commitment schedule to fix. "
            "Additionally, pandapower lacks multi-period ED, ramp rate constraints "
            "between intervals, and any temporal optimization capability. "
            "Single-period DC OPF (rundcopp) is the closest available feature."
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
