"""
Test A-11: Solve DC OPF with distributed slack (load-proportional). Compare LMPs
           to single-slack solution from A-3.

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Tool supports distributed slack formulation. LMPs differ from single-slack
    results in a physically consistent manner. Distributed slack weights are settable via API.
Tool: pandapower v3.4.0

CRITICAL NOTE: distributed_slack=True is available for runpp() (AC power flow) but
NOT for rundcopp() (DC OPF) or runopp() (AC OPF). This test checks whether distributed
slack works with DC OPF and documents the limitation.
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Test distributed slack in DC OPF and document limitations."""
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

        # 2. Single-slack DC OPF (reference from A-3)
        pp.rundcopp(net)
        if not net["OPF_converged"]:
            results["errors"].append("Single-slack DC OPF did not converge")
            return results

        single_slack_objective = float(net.res_cost)
        single_slack_lmps = net.res_bus["lam_p"].copy()
        single_slack_dispatch = net.res_gen["p_mw"].copy()
        results["details"]["single_slack_dcopf"] = {
            "converged": True,
            "objective": single_slack_objective,
            "lmp_min": float(single_slack_lmps.min()),
            "lmp_max": float(single_slack_lmps.max()),
            "lmp_mean": float(single_slack_lmps.mean()),
            "dispatch_mw": single_slack_dispatch.to_dict(),
        }

        # 3. Check if rundcopp supports distributed_slack parameter
        import inspect

        rundcopp_sig = inspect.signature(pp.rundcopp)
        rundcopp_params = list(rundcopp_sig.parameters.keys())
        has_dist_slack_dcopf = "distributed_slack" in rundcopp_params
        results["details"]["rundcopp_has_distributed_slack"] = has_dist_slack_dcopf
        results["details"]["rundcopp_parameters"] = rundcopp_params

        # 4. Check if runopp supports distributed_slack parameter
        runopp_sig = inspect.signature(pp.runopp)
        runopp_params = list(runopp_sig.parameters.keys())
        has_dist_slack_acopf = "distributed_slack" in runopp_params
        results["details"]["runopp_has_distributed_slack"] = has_dist_slack_acopf
        results["details"]["runopp_parameters"] = runopp_params

        # 5. Check runpp for distributed_slack (known to exist)
        runpp_sig = inspect.signature(pp.runpp)
        runpp_params = list(runpp_sig.parameters.keys())
        has_dist_slack_pf = "distributed_slack" in runpp_params
        results["details"]["runpp_has_distributed_slack"] = has_dist_slack_pf

        # 6. Try distributed slack with DC OPF if parameter exists
        if has_dist_slack_dcopf:
            try:
                net_dist = from_mpc(network_file, f_hz=60)
                pp.rundcopp(net_dist, distributed_slack=True)
                if net_dist["OPF_converged"]:
                    dist_slack_lmps = net_dist.res_bus["lam_p"].copy()
                    dist_slack_dispatch = net_dist.res_gen["p_mw"].copy()
                    results["details"]["distributed_slack_dcopf"] = {
                        "converged": True,
                        "objective": float(net_dist.res_cost),
                        "lmp_min": float(dist_slack_lmps.min()),
                        "lmp_max": float(dist_slack_lmps.max()),
                        "lmp_mean": float(dist_slack_lmps.mean()),
                        "dispatch_mw": dist_slack_dispatch.to_dict(),
                    }
                    # Compare LMPs
                    lmp_diff = dist_slack_lmps - single_slack_lmps
                    results["details"]["lmp_difference"] = {
                        "max_abs_diff": float(lmp_diff.abs().max()),
                        "mean_abs_diff": float(lmp_diff.abs().mean()),
                    }
                    results["status"] = "pass"
                else:
                    results["details"]["distributed_slack_dcopf"] = {"converged": False}
                    results["errors"].append("Distributed slack DC OPF did not converge")
            except TypeError as e:
                results["details"]["distributed_slack_dcopf_error"] = str(e)
                results["errors"].append(f"rundcopp rejected distributed_slack parameter: {e}")
            except Exception as e:
                results["details"]["distributed_slack_dcopf_error"] = str(e)
                results["errors"].append(
                    f"Distributed slack DC OPF failed: {type(e).__name__}: {e}"
                )
        else:
            results["details"]["distributed_slack_dcopf_note"] = (
                "rundcopp() does not accept distributed_slack parameter. "
                "Distributed slack is only available for runpp() (power flow), "
                "not for OPF formulations."
            )

        # 7. Demonstrate distributed slack works for power flow (not OPF)
        net_pf = from_mpc(network_file, f_hz=60)

        # Check if slack_weight column exists and set load-proportional weights
        if "slack_weight" not in net_pf.gen.columns:
            net_pf.gen["slack_weight"] = 0.0

        # Set load-proportional weights based on generator capacity
        total_pmax = net_pf.gen["max_p_mw"].sum()
        if total_pmax > 0:
            net_pf.gen["slack_weight"] = net_pf.gen["max_p_mw"] / total_pmax

        # Also set ext_grid slack weight
        if "slack_weight" not in net_pf.ext_grid.columns:
            net_pf.ext_grid["slack_weight"] = 0.0
        net_pf.ext_grid["slack_weight"] = 1.0  # ext_grid participates

        results["details"]["slack_weights_settable"] = True
        results["details"]["slack_weights_gen"] = net_pf.gen["slack_weight"].to_dict()

        try:
            pp.runpp(net_pf, distributed_slack=True)
            results["details"]["distributed_slack_pf"] = {
                "converged": True,
                "api": "pp.runpp(net, distributed_slack=True)",
                "note": "Distributed slack works for power flow but NOT OPF",
            }
        except Exception as e:
            results["details"]["distributed_slack_pf"] = {
                "error": f"{type(e).__name__}: {e}",
            }

        # 8. Final assessment
        if results["status"] != "pass":
            results["details"]["capability_summary"] = {
                "distributed_slack_pf": True,
                "distributed_slack_dcopf": has_dist_slack_dcopf,
                "distributed_slack_acopf": has_dist_slack_acopf,
                "slack_weights_settable": True,
            }

            if not has_dist_slack_dcopf:
                results["errors"].append(
                    "pandapower does not support distributed slack in DC OPF (rundcopp). "
                    "distributed_slack=True is only available for runpp() (power flow). "
                    "OPF formulations (rundcopp, runopp) do not accept this parameter."
                )
                results["status"] = "fail"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
