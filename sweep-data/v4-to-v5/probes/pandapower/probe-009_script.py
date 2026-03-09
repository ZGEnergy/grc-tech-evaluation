"""
Probe 009: Verify claim that in_service=False produces lambda values of 1e25.

Claim: "PYPOWER interior point solver produces lambda values of 1e25 when
generators decommitted via in_service=False"

Approach:
1. Load case39, solve DC OPF normally, record lambdas
2. Decommit one generator via in_service=False, re-solve, record lambdas
3. Also try decommitting via max_p_mw=0 for comparison
4. Report if lambda values are astronomical or reasonable
"""

import json
import time
import warnings

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc

warnings.filterwarnings("ignore")

start = time.perf_counter()
results = {}

try:
    # 1. Base case — all generators in service
    net = from_mpc("/workspace/data/networks/case39.m", f_hz=60)
    results["gen_count"] = len(net.gen)
    results["ext_grid_count"] = len(net.ext_grid)

    try:
        pp.rundcopp(net)
        base_converged = net.get("OPF_converged", False)
    except Exception as e:
        base_converged = False
        results["base_error"] = str(e)

    results["base_converged"] = base_converged
    if base_converged:
        results["base_objective"] = float(net.res_cost)
        if "lam_p" in net.res_bus.columns:
            lam_p = net.res_bus["lam_p"].values
            results["base_lambda"] = {
                "min": float(np.min(lam_p)),
                "max": float(np.max(lam_p)),
                "mean": float(np.mean(lam_p)),
                "max_abs": float(np.max(np.abs(lam_p))),
            }

    # 2. Try decommitting each generator via in_service=False
    in_service_results = []
    for gen_idx in net.gen.index:
        net2 = from_mpc("/workspace/data/networks/case39.m", f_hz=60)
        net2.gen.at[gen_idx, "in_service"] = False

        try:
            pp.rundcopp(net2)
            conv = net2.get("OPF_converged", False)
        except Exception as e:
            conv = False
            in_service_results.append(
                {
                    "gen_idx": int(gen_idx),
                    "converged": False,
                    "error": str(e),
                }
            )
            continue

        entry = {
            "gen_idx": int(gen_idx),
            "converged": conv,
        }

        if conv and "lam_p" in net2.res_bus.columns:
            lam_p = net2.res_bus["lam_p"].values
            entry["lambda_max_abs"] = float(np.max(np.abs(lam_p)))
            entry["lambda_min"] = float(np.min(lam_p))
            entry["lambda_max"] = float(np.max(lam_p))
            entry["lambda_mean"] = float(np.mean(lam_p))
            entry["objective"] = float(net2.res_cost)

            # Check for astronomical values
            if np.max(np.abs(lam_p)) > 1e10:
                entry["astronomical_lambdas"] = True
                entry["lambda_order_of_magnitude"] = int(
                    np.log10(np.max(np.abs(lam_p)))
                )
            else:
                entry["astronomical_lambdas"] = False

        in_service_results.append(entry)

    results["in_service_false_tests"] = in_service_results

    # Summary stats
    converged_in_service = [r for r in in_service_results if r.get("converged")]
    failed_in_service = [r for r in in_service_results if not r.get("converged")]
    astro_lambdas = [r for r in converged_in_service if r.get("astronomical_lambdas")]

    results["in_service_summary"] = {
        "total_tested": len(in_service_results),
        "converged": len(converged_in_service),
        "failed": len(failed_in_service),
        "astronomical_lambdas": len(astro_lambdas),
    }

    # 3. Compare with max_p_mw=0 approach
    maxp_results = []
    for gen_idx in net.gen.index:
        net3 = from_mpc("/workspace/data/networks/case39.m", f_hz=60)
        net3.gen.at[gen_idx, "max_p_mw"] = 0
        net3.gen.at[gen_idx, "min_p_mw"] = 0

        try:
            pp.rundcopp(net3)
            conv = net3.get("OPF_converged", False)
        except Exception as e:
            conv = False
            maxp_results.append(
                {
                    "gen_idx": int(gen_idx),
                    "converged": False,
                    "error": str(e),
                }
            )
            continue

        entry = {
            "gen_idx": int(gen_idx),
            "converged": conv,
        }

        if conv and "lam_p" in net3.res_bus.columns:
            lam_p = net3.res_bus["lam_p"].values
            entry["lambda_max_abs"] = float(np.max(np.abs(lam_p)))
            entry["lambda_min"] = float(np.min(lam_p))
            entry["lambda_max"] = float(np.max(lam_p))
            entry["objective"] = float(net3.res_cost)
            entry["astronomical_lambdas"] = bool(np.max(np.abs(lam_p)) > 1e10)

        maxp_results.append(entry)

    results["maxp_zero_tests"] = maxp_results

    converged_maxp = [r for r in maxp_results if r.get("converged")]
    failed_maxp = [r for r in maxp_results if not r.get("converged")]

    results["maxp_summary"] = {
        "total_tested": len(maxp_results),
        "converged": len(converged_maxp),
        "failed": len(failed_maxp),
    }

except Exception as e:
    results["error"] = f"{type(e).__name__}: {e}"
    import traceback

    results["traceback"] = traceback.format_exc()

results["wall_clock_seconds"] = round(time.perf_counter() - start, 2)
print(json.dumps(results, indent=2, default=str))
