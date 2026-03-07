"""
Test P2-2: Test piecewise-linear cost curve support

Dimension: p2_readiness
Network: TINY (IEEE 39-bus)
Pass condition: Capability (yes/no), formulation type, solver compatibility, limitations.
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case39.m") -> dict:
    """Execute PWL cost curve test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # ============================================================
        # Test 1: Piecewise-linear cost curves
        # ============================================================
        net_pwl = from_mpc(network_file, f_hz=60)

        # Remove existing cost curves
        net_pwl.poly_cost.drop(net_pwl.poly_cost.index, inplace=True)
        net_pwl.pwl_cost.drop(net_pwl.pwl_cost.index, inplace=True)

        # Add PWL costs for all generators
        # PWL format: [[p_start, p_end, marginal_cost], [p_start, p_end, marginal_cost], ...]
        # 3-segment PWL cost with increasing marginal cost
        pwl_gen_costs = {}
        for idx in net_pwl.gen.index:
            max_p = float(net_pwl.gen.at[idx, "max_p_mw"])
            min_p = float(net_pwl.gen.at[idx, "min_p_mw"])
            span = max_p - min_p
            p1 = min_p
            p2 = min_p + span * 0.33
            p3 = min_p + span * 0.66
            p4 = max_p

            # Marginal costs: $10, $20, $40 per MWh
            points = [[p1, p2, 10.0], [p2, p3, 20.0], [p3, p4, 40.0]]
            pp.create_pwl_cost(net_pwl, idx, "gen", points=points)
            pwl_gen_costs[int(idx)] = points

        # Add cost for ext_grid
        for idx in net_pwl.ext_grid.index:
            points = [[0, 500, 50.0], [500, 1500, 80.0]]
            pp.create_pwl_cost(net_pwl, idx, "ext_grid", points=points)

        results["details"]["pwl_cost_count"] = len(net_pwl.pwl_cost)
        results["details"]["pwl_sample_points"] = pwl_gen_costs.get(0, [])

        # Solve DC OPF with PWL costs
        pwl_converged = False
        try:
            pp.rundcopp(net_pwl)
            pwl_converged = net_pwl.get("OPF_converged", False)
        except Exception as e:
            results["details"]["pwl_dcopf_error"] = f"{type(e).__name__}: {e}"

        results["details"]["pwl_dcopf_converged"] = pwl_converged

        if pwl_converged:
            results["details"]["pwl_objective"] = float(net_pwl.res_cost)
            results["details"]["pwl_gen_dispatch"] = {
                int(idx): float(net_pwl.res_gen.at[idx, "p_mw"]) for idx in net_pwl.res_gen.index
            }
            results["details"]["pwl_ext_grid_p"] = float(net_pwl.res_ext_grid.at[0, "p_mw"])

            # Check LMPs
            if "lam_p" in net_pwl.res_bus.columns:
                lmps = net_pwl.res_bus["lam_p"].values
                results["details"]["pwl_lmp_range"] = {
                    "min": float(np.min(lmps)),
                    "max": float(np.max(lmps)),
                    "mean": float(np.mean(lmps)),
                }
                results["details"]["pwl_lmps_extractable"] = True
            else:
                results["details"]["pwl_lmps_extractable"] = False

        # ============================================================
        # Test 2: Quadratic (polynomial) cost curves
        # ============================================================
        net_quad = from_mpc(network_file, f_hz=60)

        # Remove existing costs
        net_quad.poly_cost.drop(net_quad.poly_cost.index, inplace=True)
        net_quad.pwl_cost.drop(net_quad.pwl_cost.index, inplace=True)

        # Add quadratic costs: c(p) = cp2 * p^2 + cp1 * p + cp0
        for idx in net_quad.gen.index:
            pp.create_poly_cost(
                net_quad,
                idx,
                "gen",
                cp2_eur_per_mw2=0.01 + 0.002 * idx,
                cp1_eur_per_mw=10.0 + 2.0 * idx,
                cp0_eur=100.0,
            )
        for idx in net_quad.ext_grid.index:
            pp.create_poly_cost(
                net_quad,
                idx,
                "ext_grid",
                cp2_eur_per_mw2=0.02,
                cp1_eur_per_mw=50.0,
                cp0_eur=0.0,
            )

        results["details"]["quad_cost_count"] = len(net_quad.poly_cost)

        # Solve DC OPF with quadratic costs
        quad_converged = False
        try:
            pp.rundcopp(net_quad)
            quad_converged = net_quad.get("OPF_converged", False)
        except Exception as e:
            results["details"]["quad_dcopf_error"] = f"{type(e).__name__}: {e}"

        results["details"]["quad_dcopf_converged"] = quad_converged

        if quad_converged:
            results["details"]["quad_objective"] = float(net_quad.res_cost)
            results["details"]["quad_gen_dispatch"] = {
                int(idx): float(net_quad.res_gen.at[idx, "p_mw"]) for idx in net_quad.res_gen.index
            }

            if "lam_p" in net_quad.res_bus.columns:
                lmps_q = net_quad.res_bus["lam_p"].values
                results["details"]["quad_lmp_range"] = {
                    "min": float(np.min(lmps_q)),
                    "max": float(np.max(lmps_q)),
                    "mean": float(np.mean(lmps_q)),
                }
                results["details"]["quad_lmps_extractable"] = True
            else:
                results["details"]["quad_lmps_extractable"] = False

        # ============================================================
        # Summary
        # ============================================================
        results["details"]["summary"] = {
            "pwl_supported": pwl_converged,
            "quadratic_supported": quad_converged,
            "pwl_api": "pp.create_pwl_cost(net, element, et, points=[[p1,c1],[p2,c2],...])",
            "quad_api": "pp.create_poly_cost(net, element, et, cp2_eur_per_mw2=..., cp1_eur_per_mw=...)",
            "solver": "PYPOWER interior point (native)",
            "formulation_type": "PWL and polynomial costs native in PYPOWER OPF model",
        }

        # Status: informational for p2_readiness
        results["status"] = "informational"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
