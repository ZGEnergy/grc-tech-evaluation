"""
Test A-10: Solve DC OPF with loss approximation. Decompose LMPs into energy,
           congestion, and loss components. Compute per-line congestion rent.

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Tool produces loss-inclusive LMPs where loss components are non-zero.
    LMP decomposition extractable. Per-line congestion rent computed and reconciled
    (5% tolerance).
Tool: pandapower v3.4.0

CRITICAL NOTE: pandapower's rundcopp() is lossless DC OPF. There is no lossy DC OPF.
AC OPF (runopp) includes losses but is not a DC formulation. No LMP decomposition
(energy/congestion/loss) is provided by either formulation.
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Attempt lossy DC OPF with LMP decomposition and document limitations."""
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

        # 2. Run standard (lossless) DC OPF for comparison
        pp.rundcopp(net)
        if not net["OPF_converged"]:
            results["errors"].append("Lossless DC OPF did not converge")
            return results

        lossless_objective = float(net.res_cost)
        lossless_lmps = net.res_bus["lam_p"].copy()
        results["details"]["lossless_dcopf"] = {
            "converged": True,
            "objective": lossless_objective,
            "lmp_min": float(lossless_lmps.min()),
            "lmp_max": float(lossless_lmps.max()),
            "lmp_mean": float(lossless_lmps.mean()),
            "lmp_uniform": bool(lossless_lmps.std() < 0.01),
        }

        # 3. Check for lossy DC OPF capability
        # rundcopp does NOT support losses
        results["details"]["lossy_dcopf_native"] = False
        results["details"]["lossy_dcopf_note"] = (
            "pandapower's rundcopp() solves lossless DC OPF. There is no parameter "
            "or option to include loss approximation in the DC formulation."
        )

        # 4. Check rundcopp kwargs for loss-related options
        import inspect

        rundcopp_sig = inspect.signature(pp.rundcopp)
        rundcopp_params = list(rundcopp_sig.parameters.keys())
        results["details"]["rundcopp_parameters"] = rundcopp_params
        loss_related_params = [p for p in rundcopp_params if "loss" in p.lower()]
        results["details"]["loss_related_params"] = (
            loss_related_params if loss_related_params else "None"
        )

        # 5. Try AC OPF as alternative (includes losses but is not DC formulation)
        try:
            net_ac = from_mpc(network_file, f_hz=60)
            pp.runopp(net_ac)
            if net_ac["OPF_converged"]:
                ac_objective = float(net_ac.res_cost)
                ac_lmps = net_ac.res_bus["lam_p"].copy()
                results["details"]["acopf_comparison"] = {
                    "converged": True,
                    "objective": ac_objective,
                    "lmp_min": float(ac_lmps.min()),
                    "lmp_max": float(ac_lmps.max()),
                    "lmp_mean": float(ac_lmps.mean()),
                    "lmp_std": float(ac_lmps.std()),
                    "includes_losses": True,
                    "is_dc_formulation": False,
                }

                # AC OPF includes losses, so LMPs differ from lossless DC
                results["details"]["objective_difference_pct"] = float(
                    100.0 * (ac_objective - lossless_objective) / lossless_objective
                )
            else:
                results["details"]["acopf_comparison"] = {"converged": False}
        except Exception as e:
            results["details"]["acopf_comparison"] = {"error": f"{type(e).__name__}: {e}"}

        # 6. Check for LMP decomposition capability
        results["details"]["lmp_decomposition_available"] = False
        results["details"]["lmp_decomposition_note"] = (
            "pandapower provides total LMPs via net.res_bus['lam_p'] but does NOT "
            "decompose them into energy, congestion, and loss components. "
            "This decomposition is not available in either rundcopp() or runopp()."
        )

        # Check what shadow price columns exist
        lam_columns = [c for c in net.res_bus.columns if c.startswith("lam_")]
        results["details"]["shadow_price_columns"] = lam_columns

        # 7. Check for congestion rent computation
        results["details"]["congestion_rent_native"] = False
        results["details"]["congestion_rent_note"] = (
            "pandapower does not compute per-line congestion rent. "
            "With lossless DC OPF, congestion rent for a line could be computed "
            "as flow * (LMP_to - LMP_from), but since LMPs lack decomposition "
            "this is only the total rent, not the congestion component."
        )

        # Compute basic congestion rent from lossless DC OPF (total, not decomposed)
        if lossless_lmps.std() > 0.001:
            # There is LMP variation - compute congestion rents
            line_flows = net.res_line["p_from_mw"].values
            # Map line endpoints to bus LMPs
            from_buses = net.line["from_bus"].values
            to_buses = net.line["to_bus"].values
            from_lmps = lossless_lmps.loc[from_buses].values
            to_lmps = lossless_lmps.loc[to_buses].values
            congestion_rents = line_flows * (to_lmps - from_lmps)
            results["details"]["congestion_rent_total"] = float(congestion_rents.sum())
            results["details"]["congestion_rent_note_2"] = (
                "Computed as flow * (LMP_to - LMP_from) from lossless DC OPF. "
                "This is total rent, not decomposed into congestion vs loss components."
            )
        else:
            results["details"]["congestion_rent_note_2"] = (
                "LMPs are nearly uniform (no congestion), so congestion rent is ~0."
            )

        # 8. Final assessment
        results["details"]["capability_summary"] = {
            "lossy_dcopf": False,
            "lmp_decomposition": False,
            "per_line_congestion_rent": False,
            "acopf_with_losses": True,
            "lossless_dcopf_lmps": True,
        }

        results["errors"].append(
            "pandapower does not support lossy DC OPF or LMP decomposition. "
            "rundcopp() is lossless only. runopp() (AC OPF) includes losses but "
            "is not a DC formulation and does not decompose LMPs. "
            "Per-line congestion rent reconciliation is not possible without "
            "LMP decomposition."
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
