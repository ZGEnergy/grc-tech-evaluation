"""
Test A-12: Multi-Period DCOPF with Storage and Congestion

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Three behavioral pass conditions:
    (1) Congestion: Mean/std of branch shadow prices by hour, >=2 of 24 hours with
        >=2 branches having non-zero shadow prices.
    (2) BESS arbitrage: Mean LMP at BESS bus during discharge hours > mean LMP during
        charge hours.
    (3) SoC feasibility: SoC in [0, energy_capacity] at all timesteps, energy balance
        consistent within 1.0 MWh.
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

# Parameters from test specification
BRANCH_DERATING = 0.70
ETA_CHARGE = 0.92
ETA_DISCHARGE = 0.95
CYCLIC_SOC = True
QUADRATIC_COSTS = True

# Differentiated cost curves
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute multi-period DC OPF with storage test."""
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

        # 1. Assess multi-period OPF capability
        # pandapower's time series module runs sequential independent PFs/OPFs
        # It does NOT formulate inter-temporal optimization

        # Check rundcopp for any multi-period parameters
        rundcopp_sig = inspect.signature(pp.rundcopp)
        rundcopp_params = list(rundcopp_sig.parameters.keys())
        results["details"]["rundcopp_parameters"] = rundcopp_params

        multiperiod_params = [
            p for p in rundcopp_params if any(kw in p.lower() for kw in ["period", "time", "step"])
        ]
        results["details"]["multiperiod_params_in_rundcopp"] = multiperiod_params

        # Check time series module
        try:
            from pandapower.timeseries import run_timeseries

            ts_sig = inspect.signature(run_timeseries)
            ts_params = list(ts_sig.parameters.keys())
            results["details"]["run_timeseries_parameters"] = ts_params
            results["details"]["timeseries_module_available"] = True
        except ImportError:
            results["details"]["timeseries_module_available"] = False

        # Check storage element
        try:
            storage_create_sig = inspect.signature(pp.create_storage)
            storage_params = list(storage_create_sig.parameters.keys())
            results["details"]["create_storage_parameters"] = storage_params
            results["details"]["storage_element_available"] = True
        except AttributeError:
            results["details"]["storage_element_available"] = False

        # Check PandaModels storage OPF
        has_pm_storage = False
        try:
            pm_storage_sig = inspect.signature(pp.runpm_storage_opf)
            pm_storage_params = list(pm_storage_sig.parameters.keys())
            results["details"]["runpm_storage_opf_parameters"] = pm_storage_params
            has_pm_storage = True
        except (AttributeError, ImportError):
            results["details"]["runpm_storage_opf_available"] = False

        # 2. Document why multi-period DCOPF is not possible natively
        results["details"]["multiperiod_assessment"] = {
            "native_multiperiod_opf": False,
            "timeseries_module_type": "sequential independent PF/OPF (no inter-temporal coupling)",
            "storage_in_opf": False,
            "storage_in_pf": True,
            "inter_temporal_soc_constraint": False,
            "pandamodels_storage_opf": has_pm_storage,
        }

        # 3. Demonstrate the limitation by running sequential DC OPFs
        # This shows what pandapower CAN do — independent per-hour OPFs without
        # inter-temporal storage optimization
        if timeseries_dir is not None:
            ts_dir = Path(timeseries_dir)

            # Load time series data
            load_24h = pd.read_csv(ts_dir / "load_24h.csv")
            bess_data = pd.read_csv(ts_dir / "bess_units.csv")
            gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

            results["details"]["load_hours"] = len(load_24h.columns) - 1  # exclude bus_id col
            results["details"]["bess_bus"] = int(bess_data["bus_id"].iloc[0])
            results["details"]["bess_power_mw"] = float(bess_data["power_mw"].iloc[0])
            results["details"]["bess_energy_mwh"] = float(bess_data["energy_mwh"].iloc[0])

            # Run a single-snapshot DC OPF with differentiated costs to show
            # baseline capability
            net = load_pandapower(network_file)

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
                        cp2_eur_per_mw2=costs["cp2"] if QUADRATIC_COSTS else 0.0,
                    )
                elif len(gen_match) > 0:
                    pp.create_poly_cost(
                        net,
                        element=gen_match.index[0],
                        et="gen",
                        cp1_eur_per_mw=costs["cp1"],
                        cp2_eur_per_mw2=costs["cp2"] if QUADRATIC_COSTS else 0.0,
                    )

            # Derate branches
            net.line["max_loading_percent"] = 100.0
            net.line["max_i_ka"] = net.line["max_i_ka"] * BRANCH_DERATING
            if len(net.trafo) > 0:
                net.trafo["max_loading_percent"] = 100.0

            # Add storage element (to show API exists, even though OPF won't
            # optimize it inter-temporally)
            bess_bus_pp = int(bess_data["bus_id"].iloc[0]) - 1
            try:
                storage_idx = pp.create_storage(
                    net,
                    bus=bess_bus_pp,
                    p_mw=0.0,
                    max_e_mwh=float(bess_data["energy_mwh"].iloc[0]),
                    min_e_mwh=float(bess_data["energy_mwh"].iloc[0])
                    * float(bess_data["min_soc"].iloc[0]),
                    soc_percent=float(bess_data["init_soc"].iloc[0]) * 100.0,
                    controllable=True,
                    min_p_mw=-float(bess_data["power_mw"].iloc[0]),
                    max_p_mw=float(bess_data["power_mw"].iloc[0]),
                )
                results["details"]["storage_created"] = True
                results["details"]["storage_index"] = int(storage_idx)

                # Add cost for storage (zero marginal cost)
                pp.create_poly_cost(
                    net,
                    element=storage_idx,
                    et="storage",
                    cp1_eur_per_mw=0.0,
                    cp0_eur=0.0,
                )
            except Exception as e:
                results["details"]["storage_creation_error"] = f"{type(e).__name__}: {e}"

            # Solve single snapshot to demonstrate OPF works
            pp.rundcopp(net)
            snapshot_converged = net.OPF_converged
            results["details"]["single_snapshot_dcopf_converged"] = snapshot_converged

            if snapshot_converged:
                results["details"]["single_snapshot_objective"] = (
                    float(net._ppc["f"]) if "f" in net._ppc else None
                )
                # Storage dispatch in single snapshot
                if len(net.res_storage) > 0:
                    results["details"]["storage_dispatch_mw"] = float(
                        net.res_storage["p_mw"].iloc[0]
                    )

            # 4. Demonstrate that run_timeseries does NOT provide inter-temporal
            # optimization — it would run independent OPFs per hour
            results["details"]["sequential_opf_limitation"] = (
                "pandapower.timeseries.run_timeseries() can loop rundcopp() over "
                "24 hours, but each hour's OPF is independent. There is no "
                "inter-temporal SoC constraint linking storage dispatch across hours. "
                "The storage element's SoC would need to be manually tracked via a "
                "custom controller, but the optimization would not 'see' future hours "
                "when deciding current-hour dispatch. This is fundamentally different "
                "from multi-period DCOPF where all 24 hours are co-optimized."
            )

        # 5. Final assessment
        results["details"]["finding"] = (
            "pandapower cannot express multi-period DCOPF with inter-temporal storage "
            "constraints. The DC OPF (rundcopp) is a single-period formulation. The "
            "timeseries module runs sequential independent solves without inter-temporal "
            "coupling. Storage elements exist for power flow tracking but do not "
            "participate in OPF co-optimization across time periods. The PandaModels.jl "
            "bridge has runpm_storage_opf() which could potentially provide multi-period "
            f"storage OPF, but {'is' if has_pm_storage else 'is not'} available in the "
            "current environment. Implementing multi-period DCOPF with storage would "
            "require building a custom optimization model (e.g., via Pyomo) outside "
            "pandapower's native capabilities."
        )

        results["details"]["capability_assessment"] = {
            "single_period_dcopf": True,
            "multiperiod_dcopf": False,
            "storage_element": True,
            "storage_in_opf": True,
            "inter_temporal_soc": False,
            "cyclic_soc_constraint": False,
            "congestion_shadow_prices": True,
            "bess_arbitrage_optimization": False,
        }

        results["errors"].append(
            "pandapower has no multi-period DCOPF formulation. The DC OPF is "
            "single-period only, and the timeseries module runs sequential independent "
            "OPFs without inter-temporal storage constraints. All three behavioral "
            "pass conditions (congestion reporting across hours, BESS arbitrage timing, "
            "SoC feasibility trajectory) require co-optimization across 24 hours, which "
            "is architecturally impossible in pandapower's native OPF."
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
