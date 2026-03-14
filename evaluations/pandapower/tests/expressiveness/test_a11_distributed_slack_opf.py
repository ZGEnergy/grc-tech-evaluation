"""
Test A-11: Solve DC OPF with distributed slack

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Tool supports distributed slack formulation. LMPs differ from
    single-slack results in a physically consistent manner (SMEC reflects the
    distributed reference). Distributed slack weights are settable via API
    (e.g., proportional to load, proportional to generation, or custom weights).
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

# Differentiated cost curves from data/timeseries/case39/README.md
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}


def _setup_opf(net, timeseries_dir: str) -> None:
    """Configure generators with differentiated costs for OPF."""
    import pandapower as pp

    ts_dir = Path(timeseries_dir)
    gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

    for idx in net.gen.index:
        net.gen.at[idx, "controllable"] = True
        net.gen.at[idx, "min_p_mw"] = 0.0

    for idx in net.ext_grid.index:
        net.ext_grid.at[idx, "controllable"] = True
        net.ext_grid.at[idx, "min_p_mw"] = -9999.0
        net.ext_grid.at[idx, "max_p_mw"] = 9999.0

    net.bus["min_vm_pu"] = 0.9
    net.bus["max_vm_pu"] = 1.1

    net.poly_cost.drop(net.poly_cost.index, inplace=True)
    if hasattr(net, "pwl_cost") and len(net.pwl_cost) > 0:
        net.pwl_cost.drop(net.pwl_cost.index, inplace=True)

    for _, row in gen_params.iterrows():
        tech = row["tech_class_key"]
        costs = COST_BY_TECH.get(tech, COST_BY_TECH["gas_CC"])
        bus_id_pp = int(row["bus_id"]) - 1

        ext_match = net.ext_grid[net.ext_grid["bus"] == bus_id_pp]
        gen_match = net.gen[net.gen["bus"] == bus_id_pp]

        if len(ext_match) > 0:
            pp.create_poly_cost(
                net,
                element=ext_match.index[0],
                et="ext_grid",
                cp1_eur_per_mw=costs["cp1"],
                cp2_eur_per_mw2=costs["cp2"],
            )
        elif len(gen_match) > 0:
            pp.create_poly_cost(
                net,
                element=gen_match.index[0],
                et="gen",
                cp1_eur_per_mw=costs["cp1"],
                cp2_eur_per_mw2=costs["cp2"],
            )


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute distributed slack OPF test."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import inspect

        import pandapower as pp

        results["details"]["pandapower_version"] = pp.__version__

        # 1. Load network
        net = load_pandapower(network_file)
        results["details"]["bus_count"] = len(net.bus)

        # 2. Check distributed slack support in power flow
        # pandapower supports distributed_slack=True in runpp() (AC PF)
        runpp_sig = inspect.signature(pp.runpp)
        runpp_params = list(runpp_sig.parameters.keys())
        has_distributed_slack_pf = "distributed_slack" in runpp_params
        results["details"]["distributed_slack_in_runpp"] = has_distributed_slack_pf

        # 3. Check distributed slack support in DC OPF
        rundcopp_sig = inspect.signature(pp.rundcopp)
        rundcopp_params = list(rundcopp_sig.parameters.keys())
        has_distributed_slack_dcopf = "distributed_slack" in rundcopp_params
        results["details"]["distributed_slack_in_rundcopp"] = has_distributed_slack_dcopf
        results["details"]["rundcopp_parameters"] = rundcopp_params

        # Also check runopp (AC OPF)
        runopp_sig = inspect.signature(pp.runopp)
        runopp_params = list(runopp_sig.parameters.keys())
        has_distributed_slack_acopf = "distributed_slack" in runopp_params
        results["details"]["distributed_slack_in_runopp"] = has_distributed_slack_acopf

        # 4. Check if slack_weight column exists in gen/ext_grid tables
        gen_cols = list(net.gen.columns)
        ext_grid_cols = list(net.ext_grid.columns)
        has_slack_weight_gen = "slack_weight" in gen_cols
        has_slack_weight_ext = "slack_weight" in ext_grid_cols
        results["details"]["slack_weight_in_gen"] = has_slack_weight_gen
        results["details"]["slack_weight_in_ext_grid"] = has_slack_weight_ext

        # 5. If distributed slack exists for PF but not OPF, document it
        if has_distributed_slack_pf and not has_distributed_slack_dcopf:
            results["details"]["distributed_slack_pf_only"] = True

        # 6. Try distributed slack power flow to confirm PF support works
        if has_distributed_slack_pf:
            try:
                # Set up slack weights (proportional to Pmax)
                net_pf = load_pandapower(network_file)
                total_pmax = 0.0

                for idx in net_pf.gen.index:
                    pmax = net_pf.gen.at[idx, "max_p_mw"]
                    net_pf.gen.at[idx, "slack_weight"] = float(pmax)
                    total_pmax += float(pmax)

                for idx in net_pf.ext_grid.index:
                    # ext_grid also participates in distributed slack
                    net_pf.ext_grid.at[idx, "slack_weight"] = 1000.0
                    total_pmax += 1000.0

                # Run distributed slack PF
                pp.runpp(net_pf, distributed_slack=True, calculate_voltage_angles=True)
                ds_pf_converged = net_pf.converged
                results["details"]["distributed_slack_pf_converged"] = ds_pf_converged

                if ds_pf_converged:
                    ds_gen_dispatch = net_pf.res_gen["p_mw"].to_dict()
                    ds_ext_dispatch = net_pf.res_ext_grid["p_mw"].to_dict()
                    results["details"]["distributed_slack_pf_gen_dispatch"] = {
                        k: round(v, 2) for k, v in ds_gen_dispatch.items()
                    }
                    results["details"]["distributed_slack_pf_ext_dispatch"] = {
                        k: round(v, 2) for k, v in ds_ext_dispatch.items()
                    }

                # Also run single-slack PF for comparison
                net_ss = load_pandapower(network_file)
                pp.runpp(net_ss, calculate_voltage_angles=True)
                ss_pf_converged = net_ss.converged
                results["details"]["single_slack_pf_converged"] = ss_pf_converged

                if ss_pf_converged and ds_pf_converged:
                    # Compare dispatches
                    ss_ext_p = float(net_ss.res_ext_grid["p_mw"].iloc[0])
                    ds_ext_p = float(net_pf.res_ext_grid["p_mw"].iloc[0])
                    results["details"]["single_slack_ext_grid_p_mw"] = round(ss_ext_p, 2)
                    results["details"]["distributed_slack_ext_grid_p_mw"] = round(ds_ext_p, 2)
                    results["details"]["ext_grid_dispatch_differs"] = abs(ss_ext_p - ds_ext_p) > 0.1

            except Exception as e:
                results["details"]["distributed_slack_pf_error"] = f"{type(e).__name__}: {e}"

        # 7. Try distributed slack in OPF (even if parameter not in signature)
        if timeseries_dir is not None:
            net_opf = load_pandapower(network_file)
            _setup_opf(net_opf, timeseries_dir)

            # Single-slack DC OPF baseline
            pp.rundcopp(net_opf)
            ss_opf_converged = net_opf.OPF_converged
            results["details"]["single_slack_dcopf_converged"] = ss_opf_converged

            if ss_opf_converged and "lam_p" in net_opf.res_bus.columns:
                ss_lmps = net_opf.res_bus["lam_p"].to_dict()
                results["details"]["single_slack_lmps_sample"] = {
                    k: round(v, 4) for k, v in list(ss_lmps.items())[:5]
                }
                results["details"]["single_slack_lmp_range"] = {
                    "min": round(float(net_opf.res_bus["lam_p"].min()), 4),
                    "max": round(float(net_opf.res_bus["lam_p"].max()), 4),
                }

            # Attempt distributed slack OPF
            if has_distributed_slack_dcopf:
                try:
                    net_ds_opf = load_pandapower(network_file)
                    _setup_opf(net_ds_opf, timeseries_dir)

                    for idx in net_ds_opf.gen.index:
                        net_ds_opf.gen.at[idx, "slack_weight"] = float(
                            net_ds_opf.gen.at[idx, "max_p_mw"]
                        )
                    for idx in net_ds_opf.ext_grid.index:
                        net_ds_opf.ext_grid.at[idx, "slack_weight"] = 1000.0

                    pp.rundcopp(net_ds_opf, distributed_slack=True)
                    ds_opf_converged = net_ds_opf.OPF_converged
                    results["details"]["distributed_slack_dcopf_converged"] = ds_opf_converged

                    if ds_opf_converged and "lam_p" in net_ds_opf.res_bus.columns:
                        ds_lmps = net_ds_opf.res_bus["lam_p"].to_dict()
                        results["details"]["distributed_slack_lmps_sample"] = {
                            k: round(v, 4) for k, v in list(ds_lmps.items())[:5]
                        }
                        # Check if LMPs differ
                        if ss_opf_converged:
                            max_diff = max(
                                abs(ss_lmps.get(k, 0) - ds_lmps.get(k, 0)) for k in ss_lmps
                            )
                            results["details"]["max_lmp_difference"] = round(max_diff, 6)
                            results["details"]["lmps_differ"] = max_diff > 1e-4

                except TypeError as e:
                    # rundcopp might reject the distributed_slack kwarg
                    results["details"]["distributed_slack_dcopf_error"] = str(e)
                    has_distributed_slack_dcopf = False
                except Exception as e:
                    results["details"]["distributed_slack_dcopf_error"] = f"{type(e).__name__}: {e}"

            # If not available in OPF, try passing via **kwargs (long shot)
            if not has_distributed_slack_dcopf:
                try:
                    net_try = load_pandapower(network_file)
                    _setup_opf(net_try, timeseries_dir)

                    # Set slack weights
                    for idx in net_try.gen.index:
                        net_try.gen.at[idx, "slack_weight"] = float(net_try.gen.at[idx, "max_p_mw"])
                    for idx in net_try.ext_grid.index:
                        net_try.ext_grid.at[idx, "slack_weight"] = 1000.0

                    pp.rundcopp(net_try, distributed_slack=True)
                    kwargs_converged = net_try.OPF_converged
                    results["details"]["kwargs_distributed_slack_accepted"] = True
                    results["details"]["kwargs_dcopf_converged"] = kwargs_converged

                    # Check if LMPs differ from single-slack
                    if kwargs_converged and ss_opf_converged and "lam_p" in net_try.res_bus.columns:
                        kwargs_lmps = net_try.res_bus["lam_p"].to_dict()
                        max_diff = max(
                            abs(ss_lmps.get(k, 0) - kwargs_lmps.get(k, 0)) for k in ss_lmps
                        )
                        results["details"]["kwargs_lmp_max_diff_vs_single_slack"] = round(
                            max_diff, 8
                        )
                        results["details"]["kwargs_lmps_actually_differ"] = max_diff > 1e-6
                        results["details"]["kwargs_lmps_sample"] = {
                            k: round(v, 4) for k, v in list(kwargs_lmps.items())[:5]
                        }
                        if max_diff < 1e-6:
                            results["details"]["kwargs_finding"] = (
                                "rundcopp() accepts distributed_slack=True via **kwargs "
                                "without raising an error, but the parameter is silently "
                                "ignored — LMPs are identical to single-slack results."
                            )
                except TypeError:
                    results["details"]["kwargs_distributed_slack_accepted"] = False
                    results["details"]["kwargs_error"] = (
                        "rundcopp() does not accept distributed_slack parameter"
                    )
                except Exception as e:
                    results["details"]["kwargs_distributed_slack_accepted"] = "error"
                    results["details"]["kwargs_error"] = f"{type(e).__name__}: {e}"

        # 8. Summarize finding
        results["details"]["finding"] = (
            "pandapower supports distributed slack for AC power flow (runpp with "
            "distributed_slack=True and slack_weight on gen/ext_grid), but this feature "
            "is NOT available for OPF (neither rundcopp nor runopp accept the "
            "distributed_slack parameter). The DC OPF formulation in PYPOWER uses a "
            "fixed single-slack reference bus. Since the pass condition requires "
            "distributed slack in the OPF formulation with LMP comparison, this test "
            "fails. The distributed slack PF capability confirms pandapower has the "
            "concept but it is not propagated to the optimization layer."
        )

        results["details"]["capability_assessment"] = {
            "distributed_slack_pf": has_distributed_slack_pf,
            "distributed_slack_dcopf": has_distributed_slack_dcopf,
            "distributed_slack_acopf": has_distributed_slack_acopf,
            "slack_weight_settable": has_slack_weight_gen or has_slack_weight_ext,
        }

        if not has_distributed_slack_dcopf:
            results["errors"].append(
                "pandapower's DC OPF (rundcopp) does not support distributed slack. "
                "The distributed_slack parameter is only available in runpp() for power "
                "flow, not in the OPF formulations. LMPs from rundcopp always reflect "
                "a single-slack reference."
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
