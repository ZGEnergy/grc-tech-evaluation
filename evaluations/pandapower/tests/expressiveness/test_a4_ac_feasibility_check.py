"""
Test A-4: AC feasibility check on DC OPF dispatch

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Achievable within the same model context (no export to file and
    reimport). Voltage violations and thermal limit violations identifiable from
    results.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

# Same cost mapping as A-3
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}

BRANCH_DERATING = 0.70

# Voltage violation thresholds
VM_MIN = 0.95
VM_MAX = 1.05


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute AC feasibility check on DC OPF dispatch."""
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

        # =========================================================
        # STEP 1: Solve DC OPF (same as A-3, within same context)
        # =========================================================
        net = load_pandapower(network_file)

        results["details"]["base_mva"] = float(net.sn_mva)
        results["details"]["bus_count"] = len(net.bus)

        # Load differentiated costs
        if timeseries_dir is None:
            results["errors"].append("timeseries_dir is required for A-4 TINY")
            return results

        ts_dir = Path(timeseries_dir)
        gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

        # Set up generators for OPF
        for idx in net.gen.index:
            net.gen.at[idx, "controllable"] = True
            net.gen.at[idx, "min_p_mw"] = 0.0

        for idx in net.ext_grid.index:
            net.ext_grid.at[idx, "controllable"] = True
            net.ext_grid.at[idx, "min_p_mw"] = -9999.0
            net.ext_grid.at[idx, "max_p_mw"] = 9999.0

        net.bus["min_vm_pu"] = 0.9
        net.bus["max_vm_pu"] = 1.1

        # Clear existing cost functions
        net.poly_cost.drop(net.poly_cost.index, inplace=True)
        if hasattr(net, "pwl_cost"):
            net.pwl_cost.drop(net.pwl_cost.index, inplace=True)

        # Apply costs
        for _, row in gen_params.iterrows():
            tech = row["tech_class_key"]
            costs = COST_BY_TECH.get(tech, COST_BY_TECH["gas_CC"])
            # gen_temporal_params uses 1-indexed MATPOWER bus IDs;
            # pandapower from_mpc uses 0-indexed buses
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

        # Derate branches
        net.line["max_loading_percent"] = 100.0
        net.line["max_i_ka"] *= BRANCH_DERATING
        if len(net.trafo) > 0:
            net.trafo["max_loading_percent"] = 100.0

        # Solve DC OPF
        pp.rundcopp(net)
        if not net.OPF_converged:
            results["errors"].append("DC OPF did not converge (prerequisite for A-4)")
            return results

        # Record DC OPF dispatch
        dcopf_gen_dispatch = net.res_gen["p_mw"].copy()
        dcopf_ext_grid_dispatch = net.res_ext_grid["p_mw"].copy()
        results["details"]["dcopf_gen_dispatch_mw"] = dcopf_gen_dispatch.to_dict()
        results["details"]["dcopf_ext_grid_dispatch_mw"] = dcopf_ext_grid_dispatch.to_dict()
        results["details"]["dcopf_total_gen_mw"] = float(
            dcopf_gen_dispatch.sum() + dcopf_ext_grid_dispatch.sum()
        )

        # Log units for cross-tool consistency
        results["details"]["dispatch_units"] = "MW"
        results["details"]["limit_units"] = "MW (via max_i_ka and vn_kv)"
        results["details"]["base_power_mva"] = float(net.sn_mva)

        # =========================================================
        # STEP 2: Fix dispatch and run ACPF (same model context)
        # =========================================================

        # Fix generator active power to DC OPF dispatch values
        # In pandapower, generators are PV buses: we fix p_mw and let
        # the solver find Q and voltage angles
        for idx in net.gen.index:
            net.gen.at[idx, "p_mw"] = dcopf_gen_dispatch.at[idx]

        # ext_grid p_mw is set by the solver as slack; we keep it as-is
        # since ext_grid will absorb any imbalance

        # Restore original line ratings for AC feasibility check
        # (use original ratings to check violations, not derated ones)
        net.line["max_i_ka"] = net.line["max_i_ka"] / BRANCH_DERATING

        # Run AC power flow with DC warm start
        acpf_start = time.perf_counter()
        pp.runpp(
            net,
            algorithm="nr",
            init="dc",
            calculate_voltage_angles=True,
            tolerance_mva=1e-8,
            max_iteration=30,
        )
        acpf_time = time.perf_counter() - acpf_start
        results["details"]["acpf_solve_seconds"] = acpf_time

        ac_converged = net.converged
        results["details"]["acpf_converged"] = ac_converged

        if not ac_converged:
            # Try flat start as fallback
            pp.runpp(
                net,
                algorithm="nr",
                init="flat",
                calculate_voltage_angles=True,
                tolerance_mva=1e-8,
                max_iteration=30,
            )
            ac_converged = net.converged
            results["details"]["acpf_flat_start_converged"] = ac_converged
            if not ac_converged:
                results["errors"].append(
                    "ACPF did not converge on DC OPF dispatch "
                    "(tried both DC and flat initialization)"
                )
                return results

        # =========================================================
        # STEP 3: Identify violations from AC results
        # =========================================================

        # Voltage violations
        vm = net.res_bus["vm_pu"]
        voltage_violations_low = vm[vm < VM_MIN]
        voltage_violations_high = vm[vm > VM_MAX]
        results["details"]["voltage_violations"] = {
            "low_count": len(voltage_violations_low),
            "high_count": len(voltage_violations_high),
            "total_count": len(voltage_violations_low) + len(voltage_violations_high),
            "vm_min": float(vm.min()),
            "vm_max": float(vm.max()),
            "threshold_low": VM_MIN,
            "threshold_high": VM_MAX,
        }
        if len(voltage_violations_low) > 0:
            results["details"]["voltage_violations"]["low_buses"] = {
                int(k): float(v) for k, v in voltage_violations_low.items()
            }
        if len(voltage_violations_high) > 0:
            results["details"]["voltage_violations"]["high_buses"] = {
                int(k): float(v) for k, v in voltage_violations_high.items()
            }

        # Thermal limit violations (line loading > 100%)
        line_loading = net.res_line["loading_percent"]
        thermal_violations = line_loading[line_loading > 100.0]
        results["details"]["thermal_violations"] = {
            "count": len(thermal_violations),
            "max_loading_pct": float(line_loading.max()),
        }
        if len(thermal_violations) > 0:
            results["details"]["thermal_violations"]["violated_lines"] = {
                int(k): float(v) for k, v in thermal_violations.items()
            }

        # Trafo loading violations
        if len(net.res_trafo) > 0:
            trafo_loading = net.res_trafo["loading_percent"]
            trafo_violations = trafo_loading[trafo_loading > 100.0]
            results["details"]["trafo_violations"] = {
                "count": len(trafo_violations),
                "max_loading_pct": float(trafo_loading.max()),
            }

        # Reactive power limit violations
        gen_q = net.res_gen["q_mvar"]
        q_violations = 0
        if "max_q_mvar" in net.gen.columns and "min_q_mvar" in net.gen.columns:
            for idx in net.gen.index:
                q = gen_q.at[idx]
                q_max = net.gen.at[idx, "max_q_mvar"]
                q_min = net.gen.at[idx, "min_q_mvar"]
                if not np.isnan(q_max) and q > q_max + 0.1:
                    q_violations += 1
                if not np.isnan(q_min) and q < q_min - 0.1:
                    q_violations += 1
        results["details"]["reactive_power_violations"] = q_violations

        # AC vs DC dispatch comparison
        ac_gen_p = net.res_gen["p_mw"]
        p_diff = (ac_gen_p - dcopf_gen_dispatch).abs()
        results["details"]["gen_p_deviation_mw"] = {
            "max": float(p_diff.max()),
            "mean": float(p_diff.mean()),
        }

        # Total losses from AC solution
        total_p_loss = net.res_line["pl_mw"].sum()
        if len(net.res_trafo) > 0:
            total_p_loss += net.res_trafo["pl_mw"].sum()
        results["details"]["ac_total_p_loss_mw"] = float(total_p_loss)

        results["details"]["output_format"] = "pandas.DataFrame"
        results["details"]["same_model_context"] = True
        results["details"]["no_file_export_reimport"] = True

        # Pass condition: achievable within same model context,
        # violations identifiable from results
        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
