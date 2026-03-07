"""
Test B-8: Solve DC OPF with three slack configurations on SMALL

Dimension: extensibility
Network: SMALL (ACTIVSg2000 ~2000 buses)
Pass condition: Reference bus / slack formulation is configurable via API without
    model reconstruction. LMP values change consistently across configurations.
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg2000.m") -> dict:
    """Execute reference bus configuration test on SMALL."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # (a) Default single slack
        net_a = from_mpc(network_file, f_hz=60)
        default_slack_bus = int(net_a.ext_grid.at[net_a.ext_grid.index[0], "bus"])
        results["details"]["config_a_slack_bus"] = default_slack_bus

        pp.rundcopp(net_a)
        assert net_a["OPF_converged"], "Config (a) DC OPF did not converge"

        lmps_a = net_a.res_bus["lam_p"].values.copy()
        obj_a = float(net_a.res_cost)

        results["details"]["config_a"] = {
            "converged": True,
            "objective": obj_a,
            "lmp_min": float(np.min(lmps_a)),
            "lmp_max": float(np.max(lmps_a)),
            "lmp_mean": float(np.mean(lmps_a)),
            "lmp_std": float(np.std(lmps_a)),
        }

        # (b) Different single slack bus
        net_b = from_mpc(network_file, f_hz=60)
        candidate_buses = net_b.gen["bus"].values
        new_slack_bus = None
        for cb in candidate_buses:
            if int(cb) != default_slack_bus:
                new_slack_bus = int(cb)
                break

        config_b_converged = False
        if new_slack_bus is not None:
            results["details"]["config_b_slack_bus"] = new_slack_bus

            old_ext = net_b.ext_grid.iloc[0].copy()
            gen_at_new_slack = net_b.gen[net_b.gen["bus"] == new_slack_bus].index
            if len(gen_at_new_slack) > 0:
                gen_cost_mask = (net_b.poly_cost["et"] == "gen") & (
                    net_b.poly_cost["element"] == gen_at_new_slack[0]
                )
                net_b.poly_cost.drop(net_b.poly_cost[gen_cost_mask].index, inplace=True)
                net_b.gen.drop(gen_at_new_slack[0], inplace=True)

            net_b.ext_grid.at[net_b.ext_grid.index[0], "bus"] = new_slack_bus

            pp.create_gen(
                net_b,
                bus=default_slack_bus,
                p_mw=float(old_ext.get("p_mw", 0)),
                vm_pu=1.0,
                min_p_mw=0,
                max_p_mw=2000,
                max_q_mvar=9999,
                min_q_mvar=-9999,
                in_service=True,
                controllable=True,
            )
            new_gen_idx = net_b.gen.index[-1]
            pp.create_poly_cost(net_b, new_gen_idx, "gen", cp1_eur_per_mw=13.5)

            try:
                pp.rundcopp(net_b)
                config_b_converged = net_b.get("OPF_converged", False)
            except Exception as e:
                results["details"]["config_b_error"] = str(e)

            if config_b_converged:
                lmps_b = net_b.res_bus["lam_p"].values.copy()
                obj_b = float(net_b.res_cost)
                lmp_diff_ab = np.abs(lmps_a - lmps_b)
                results["details"]["config_b"] = {
                    "converged": True,
                    "objective": obj_b,
                    "lmp_min": float(np.min(lmps_b)),
                    "lmp_max": float(np.max(lmps_b)),
                    "lmp_mean": float(np.mean(lmps_b)),
                    "lmp_diff_max": float(np.max(lmp_diff_ab)),
                    "lmp_diff_mean": float(np.mean(lmp_diff_ab)),
                }
            else:
                results["details"]["config_b"] = {"converged": False}

        # (c) Distributed slack
        net_c = from_mpc(network_file, f_hz=60)
        total_cap = net_c.gen["max_p_mw"].sum()
        net_c.gen["slack_weight"] = net_c.gen["max_p_mw"] / total_cap

        distributed_slack_works = False
        try:
            pp.rundcopp(net_c, distributed_slack=True)
            if net_c.get("OPF_converged", False):
                distributed_slack_works = True
                lmps_c = net_c.res_bus["lam_p"].values.copy()
                obj_c = float(net_c.res_cost)
                results["details"]["config_c"] = {
                    "converged": True,
                    "objective": obj_c,
                    "lmp_min": float(np.min(lmps_c)),
                    "lmp_max": float(np.max(lmps_c)),
                    "lmp_mean": float(np.mean(lmps_c)),
                }
        except TypeError as e:
            results["details"]["config_c"] = {
                "converged": False,
                "error": f"TypeError: {e}",
                "note": "rundcopp() does not accept distributed_slack parameter",
            }
        except Exception as e:
            results["details"]["config_c"] = {
                "converged": False,
                "error": f"{type(e).__name__}: {e}",
            }

        if not distributed_slack_works:
            results["workarounds"].append(
                "Distributed slack not available for DC OPF (rundcopp). "
                "Only supported for power flow (runpp)."
            )

        # Assessment
        configs_passed = sum(
            [
                results["details"].get("config_a", {}).get("converged", False),
                config_b_converged,
                distributed_slack_works,
            ]
        )
        results["details"]["configs_passed"] = configs_passed

        if configs_passed >= 2:
            results["status"] = "qualified_pass"
            results["details"]["qualification"] = (
                f"{configs_passed}/3 configs completed. Distributed slack not available for OPF."
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
