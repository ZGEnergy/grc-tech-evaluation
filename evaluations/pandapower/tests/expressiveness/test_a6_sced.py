"""
Test A-6: Fix commitment from A-5, solve economic dispatch

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Solves. Dispatch schedule extractable. UC and ED are cleanly
    separable as a two-stage workflow. Ramp rate constraints are demonstrably
    enforced between consecutive dispatch intervals in the ED stage.
Tool: pandapower 3.4.0

Since A-5 fails (no SCUC in pandapower), A-6 is at most ed_only.
This test attempts multi-period economic dispatch via sequential single-period
DC OPF calls with manual ramp constraints applied between periods.
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

# Differentiated cost curves (same as A-3)
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}

BRANCH_DERATING = 0.70


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute SCED test -- A-5 failed, so attempt ed_only mode.

    Attempts sequential single-period DC OPF with manual ramp enforcement.
    pandapower has no native multi-period dispatch, so ramp constraints must
    be applied manually by adjusting generator Pmin/Pmax between periods.
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
        import pandapower as pp

        results["details"]["pandapower_version"] = pp.__version__
        results["details"]["sced_mode"] = "ed_only"
        results["details"]["a5_status"] = "fail"
        results["details"]["commitment_source"] = "all_generators_on"

        if timeseries_dir is None:
            results["errors"].append("timeseries_dir is required for A-6 TINY")
            return results

        ts_dir = Path(timeseries_dir)
        gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")
        load_24h = pd.read_csv(ts_dir / "load_24h.csv")

        # Load network
        net = load_pandapower(network_file)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen) + len(net.ext_grid)

        # Build ramp rate lookup (MW/hr from gen_temporal_params)
        ramp_rates = {}  # bus_id_pp -> ramp_rate_mw_per_hr
        for _, row in gen_params.iterrows():
            bus_id_pp = int(row["bus_id"]) - 1  # Convert 1-indexed to 0-indexed
            ramp_rates[bus_id_pp] = float(row["ramp_rate_mw_per_hr"])

        # Setup: apply differentiated costs and branch derating
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
                    cp0_eur=0.0,
                )
            elif len(gen_match) > 0:
                pp.create_poly_cost(
                    net,
                    element=gen_match.index[0],
                    et="gen",
                    cp1_eur_per_mw=costs["cp1"],
                    cp2_eur_per_mw2=costs["cp2"],
                    cp0_eur=0.0,
                )

        # Branch derating
        net.line["max_loading_percent"] = 100.0
        net.line["max_i_ka"] = net.line["max_i_ka"] * BRANCH_DERATING
        if len(net.trafo) > 0:
            net.trafo["max_loading_percent"] = 100.0

        # Save original Pmin/Pmax for ramp constraint application
        orig_gen_pmin = net.gen["min_p_mw"].copy()
        orig_gen_pmax = net.gen["max_p_mw"].copy()
        orig_ext_pmin = net.ext_grid["min_p_mw"].copy()
        orig_ext_pmax = net.ext_grid["max_p_mw"].copy()

        # load_24h.csv has columns: bus_id, HR_1, HR_2, ..., HR_24

        # Sequential 24-hour dispatch
        dispatch_matrix = []  # List of dicts, one per hour
        total_cost = 0.0
        prev_dispatch = None  # {bus_id_pp: mw_dispatch}
        ramp_binding_count = 0
        solve_time = 0.0
        n_hours = 24

        for hr in range(1, n_hours + 1):
            hr_col = f"HR_{hr}"

            # Scale loads for this hour
            for _, lrow in load_24h.iterrows():
                bus_id_1indexed = int(lrow["bus_id"])
                bus_id_pp = bus_id_1indexed - 1
                target_load_mw = float(lrow[hr_col])

                # Find loads at this bus and scale them
                load_mask = net.load["bus"] == bus_id_pp
                if load_mask.any():
                    # Scale proportionally
                    current_total = net.load.loc[load_mask, "p_mw"].sum()
                    if current_total > 0:
                        scale = target_load_mw / current_total
                        net.load.loc[load_mask, "p_mw"] = net.load.loc[load_mask, "p_mw"] * scale

            # Apply ramp constraints from previous hour's dispatch
            if prev_dispatch is not None:
                for idx in net.gen.index:
                    bus = int(net.gen.at[idx, "bus"])
                    if bus in ramp_rates and bus in prev_dispatch:
                        ramp_mw = ramp_rates[bus]
                        prev_p = prev_dispatch[bus]
                        ramp_lo = max(float(orig_gen_pmin.at[idx]), prev_p - ramp_mw)
                        ramp_hi = min(float(orig_gen_pmax.at[idx]), prev_p + ramp_mw)
                        net.gen.at[idx, "min_p_mw"] = ramp_lo
                        net.gen.at[idx, "max_p_mw"] = ramp_hi
                    else:
                        net.gen.at[idx, "min_p_mw"] = float(orig_gen_pmin.at[idx])
                        net.gen.at[idx, "max_p_mw"] = float(orig_gen_pmax.at[idx])

                for idx in net.ext_grid.index:
                    bus = int(net.ext_grid.at[idx, "bus"])
                    if bus in ramp_rates and bus in prev_dispatch:
                        ramp_mw = ramp_rates[bus]
                        prev_p = prev_dispatch[bus]
                        ramp_lo = prev_p - ramp_mw
                        ramp_hi = prev_p + ramp_mw
                        net.ext_grid.at[idx, "min_p_mw"] = ramp_lo
                        net.ext_grid.at[idx, "max_p_mw"] = ramp_hi
                    else:
                        net.ext_grid.at[idx, "min_p_mw"] = float(orig_ext_pmin.at[idx])
                        net.ext_grid.at[idx, "max_p_mw"] = float(orig_ext_pmax.at[idx])
            else:
                # First hour: reset to original limits
                net.gen["min_p_mw"] = orig_gen_pmin.copy()
                net.gen["max_p_mw"] = orig_gen_pmax.copy()
                net.ext_grid["min_p_mw"] = orig_ext_pmin.copy()
                net.ext_grid["max_p_mw"] = orig_ext_pmax.copy()

            # Solve DC OPF for this hour
            t0 = time.perf_counter()
            pp.rundcopp(net)
            solve_time += time.perf_counter() - t0

            if not net.OPF_converged:
                results["errors"].append(f"DC OPF did not converge at hour {hr}")
                results["details"]["failed_hour"] = hr
                return results

            # Extract dispatch
            hour_dispatch = {}
            gen_dispatch_row = {"hour": hr}

            for idx in net.gen.index:
                bus = int(net.gen.at[idx, "bus"])
                p_mw = float(net.res_gen.at[idx, "p_mw"])
                hour_dispatch[bus] = p_mw
                gen_dispatch_row[f"gen_{idx}_bus{bus}_mw"] = p_mw

            for idx in net.ext_grid.index:
                bus = int(net.ext_grid.at[idx, "bus"])
                p_mw = float(net.res_ext_grid.at[idx, "p_mw"])
                hour_dispatch[bus] = p_mw
                gen_dispatch_row[f"extgrid_{idx}_bus{bus}_mw"] = p_mw

            # Check ramp binding
            if prev_dispatch is not None:
                for bus in hour_dispatch:
                    if bus in ramp_rates and bus in prev_dispatch:
                        ramp_mw = ramp_rates[bus]
                        delta_p = abs(hour_dispatch[bus] - prev_dispatch[bus])
                        if delta_p >= ramp_mw * 0.99:  # Within 1% of ramp limit
                            ramp_binding_count += 1

            # Extract cost from net.res_cost (total objective)
            if hasattr(net, "res_cost") and net.res_cost is not None:
                hour_cost = float(net.res_cost)
                gen_dispatch_row["cost"] = hour_cost
                total_cost += hour_cost

            gen_dispatch_row["total_load_mw"] = float(net.res_load["p_mw"].sum())
            dispatch_matrix.append(gen_dispatch_row)
            prev_dispatch = hour_dispatch

        # Verify ramp enforcement
        ramp_violations = 0
        for hr_idx in range(1, len(dispatch_matrix)):
            prev_row = dispatch_matrix[hr_idx - 1]
            curr_row = dispatch_matrix[hr_idx]
            for key in curr_row:
                if key.startswith("gen_") or key.startswith("extgrid_"):
                    if key in prev_row:
                        # Parse bus from key
                        bus_str = key.split("bus")[1].split("_")[0]
                        bus = int(bus_str)
                        if bus in ramp_rates:
                            delta_p = abs(curr_row[key] - prev_row[key])
                            ramp_limit = ramp_rates[bus]
                            if delta_p > ramp_limit * 1.01:  # 1% tolerance
                                ramp_violations += 1

        results["details"]["n_hours"] = n_hours
        results["details"]["total_cost"] = f"{total_cost:.6e}"
        results["details"]["solve_time_s"] = f"{solve_time:.6e}"
        results["details"]["ramp_binding_count"] = ramp_binding_count
        results["details"]["ramp_violations"] = ramp_violations
        results["details"]["dispatch_hours_1_4"] = dispatch_matrix[:4]
        results["details"]["dispatch_hours_21_24"] = dispatch_matrix[20:]

        # Extract per-generator dispatch profile for cycling analysis
        gen_keys = [
            k for k in dispatch_matrix[0] if k.startswith("gen_") or k.startswith("extgrid_")
        ]
        gen_profiles = {}
        for key in gen_keys:
            profile = [row[key] for row in dispatch_matrix]
            gen_profiles[key] = {
                "min_mw": f"{min(profile):.2f}",
                "max_mw": f"{max(profile):.2f}",
                "range_mw": f"{max(profile) - min(profile):.2f}",
            }
        results["details"]["generator_profiles"] = gen_profiles

        # Assess result
        results["details"]["sced_mode"] = "ed_only"
        results["details"]["assessment"] = (
            "Sequential single-period DC OPF with manual ramp constraint enforcement. "
            "pandapower has no native multi-period dispatch, so ramp constraints are "
            "applied by adjusting Pmin/Pmax bounds between periods. This is NOT true "
            "SCED: (1) no commitment schedule from A-5 (all generators assumed on), "
            "(2) no temporal coupling in the optimization (each hour solved independently), "
            "(3) ramp constraints are heuristic (greedy, not globally optimal). "
            "The approach demonstrates that pandapower can be used as a building block "
            "for multi-period dispatch but does not natively support it."
        )

        results["workarounds"].append(
            "Manual ramp enforcement via Pmin/Pmax adjustment between sequential "
            "single-period DC OPF calls. Not a native capability."
        )

        # ed_only mode: dispatch is extractable, ramps enforced (manually), but
        # no commitment from A-5 and no temporal coupling in optimization.
        # This is a partial_pass at best since the workaround is fragile.
        if ramp_violations == 0 and ramp_binding_count > 0:
            results["status"] = "partial_pass"
            results["details"]["pass_rationale"] = (
                f"Dispatch extracted for all 24 hours. "
                f"Ramp constraints enforced with 0 violations and "
                f"{ramp_binding_count} binding instances. "
                f"However, this is ed_only mode (no A-5 commitment) with "
                f"manual ramp enforcement (fragile workaround)."
            )
        elif ramp_violations == 0:
            results["status"] = "partial_pass"
            results["details"]["pass_rationale"] = (
                "Dispatch extracted for all 24 hours with ramp enforcement. "
                "ed_only mode with manual workaround."
            )
        else:
            results["errors"].append(f"Ramp violations detected: {ramp_violations}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
