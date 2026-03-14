"""
Test A-12: 24-hour multi-period DCOPF with storage and congestion on Modified Tiny.

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Three behavioral checks:
    (1) Congestion reporting: Mean and std of branch shadow prices by hour. At least 2 of
        24 hours must have >=2 branches with non-zero shadow prices.
    (2) BESS arbitrage timing: Mean LMP at BESS bus during discharge hours (P > 0.01 MW)
        must exceed mean LMP during charge hours (P < -0.01 MW). Hours with |P| <= 0.01 MW
        excluded.
    (3) SoC feasibility: SoC in [0, energy_capacity] at all timesteps. Energy balance:
        |SoC[t] - SoC[t-1] - eta_ch*P_ch[t] + P_dis[t]/eta_dis| < 1.0 MWh for each t (dt=1h).
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS

Notes on GridCal battery formulation (linear_opf_ts.py):
    - Battery power: p = p_pos - p_neg, where p_pos >= 0 (discharge), p_neg >= 0 (charge)
    - Energy balance: E[t] = E[t-1] + dt * (eta_dis * p_pos - eta_ch * p_neg)
    - This formulation has the sign of the discharge term INVERTED: when discharging,
      energy should DECREASE, but the formulation INCREASES energy by eta_dis * p_pos.
    - The efficiency placement is also wrong: eta_dis should divide P_dis (you lose MORE
      stored energy than you deliver), but the formulation multiplies instead.
    - Result: the optimizer always discharges at Pmax because it sees discharge as free
      energy creation. No arbitrage behavior occurs.
    - Results are returned in MW and MWh (already multiplied by Sbase in get_values()).
"""

from __future__ import annotations

import csv
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal

# Cost mapping from gen_temporal_params.csv tech_class_key
# A-12 recipe: c2 = c1 * 0.001 (mandatory for quadratic costs)
COST_MAP = {
    "hydro": {"c1": 5.0, "c2": 0.005},
    "nuclear": {"c1": 10.0, "c2": 0.010},
    "coal_large": {"c1": 25.0, "c2": 0.025},
    "gas_CC": {"c1": 40.0, "c2": 0.040},
}

BRANCH_DERATING = 0.70

# BESS parameters from bess_units.csv
BESS_BUS_ID = 5
BESS_POWER_MW = 150.0
BESS_ENERGY_MWH = 600.0
BESS_EFFICIENCY = 0.874  # round-trip
BESS_CHARGE_EFF = 0.92  # charge efficiency (sqrt-ish split of 0.874)
BESS_DISCHARGE_EFF = 0.95  # discharge efficiency
BESS_MIN_SOC = 0.10
BESS_MAX_SOC = 0.90
BESS_INIT_SOC = 0.50


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute A-12 multi-period DCOPF with storage test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers, SolverType
        from VeraGridEngine.Simulations.OPF.opf_ts_driver import (
            OptimalPowerFlowTimeSeriesDriver,
        )

        ts_dir = Path(timeseries_dir) if timeseries_dir else None
        if ts_dir is None or not ts_dir.exists():
            results["errors"].append("timeseries_dir not found — required for A-12")
            return results

        # 1. Load network
        grid = load_gridcal(network_file)
        generators = grid.get_generators()
        buses = grid.get_buses()
        loads = grid.get_loads()
        branches = grid.get_branches()
        n_buses = grid.get_bus_number()
        n_hours = 24

        results["details"]["bus_count"] = n_buses
        results["details"]["gen_count"] = len(generators)
        results["details"]["branch_count"] = len(branches)

        # 2. Apply differentiated costs from gen_temporal_params.csv
        gen_params = {}
        with open(ts_dir / "gen_temporal_params.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                gen_params[int(row["gen_index"])] = row

        for idx, gen in enumerate(generators):
            if idx in gen_params:
                tech_key = gen_params[idx]["tech_class_key"]
                if tech_key in COST_MAP:
                    gen.Cost = COST_MAP[tech_key]["c1"]
                    gen.Cost2 = COST_MAP[tech_key]["c2"]
                    gen.Cost0 = 0.0

        results["details"]["cost_augmentation"] = "Differentiated costs applied (c2 = c1 * 0.001)"

        # 3. Apply 70% branch derating
        for branch in branches:
            if hasattr(branch, "rate") and branch.rate > 0:
                branch.rate = branch.rate * BRANCH_DERATING
            elif hasattr(branch, "Rate") and branch.Rate > 0:
                branch.Rate = branch.Rate * BRANCH_DERATING
        results["details"]["branch_derating"] = BRANCH_DERATING

        # 4. Add BESS at bus 5 (BESS_1 from bess_units.csv)
        bess_bus = None
        for b in buses:
            bus_code = b.code if hasattr(b, "code") else b.name
            if str(bus_code) == str(BESS_BUS_ID):
                bess_bus = b
                break

        if bess_bus is None:
            results["errors"].append(f"Bus {BESS_BUS_ID} not found for BESS placement")
            return results

        batt = grid.add_battery(bus=bess_bus)
        batt.name = "BESS_1"
        batt.P = 0.0
        batt.Pmax = BESS_POWER_MW
        batt.Pmin = -BESS_POWER_MW
        batt.Enom = BESS_ENERGY_MWH
        batt.min_soc = BESS_MIN_SOC
        batt.max_soc = BESS_MAX_SOC
        batt.soc_0 = BESS_INIT_SOC
        batt.soc = BESS_INIT_SOC
        batt.charge_efficiency = BESS_CHARGE_EFF
        batt.discharge_efficiency = BESS_DISCHARGE_EFF
        batt.Cost = 0.0
        batt.Cost2 = 0.0
        batt.Cost0 = 0.0
        batt.enabled_dispatch = True
        batt.active = True

        results["details"]["bess_config"] = {
            "bus": BESS_BUS_ID,
            "power_mw": BESS_POWER_MW,
            "energy_mwh": BESS_ENERGY_MWH,
            "charge_eff": BESS_CHARGE_EFF,
            "discharge_eff": BESS_DISCHARGE_EFF,
            "min_soc": BESS_MIN_SOC,
            "max_soc": BESS_MAX_SOC,
            "init_soc": BESS_INIT_SOC,
        }

        # 5. Set up time profile (24 hours)
        time_array = pd.date_range("2024-01-01", periods=n_hours, freq="h")
        unix_ts = (time_array.astype(np.int64) // 10**9).values.astype(np.int64)
        grid.set_time_profile(unix_ts)

        # 6. Set load profiles from load_24h.csv
        load_df = pd.read_csv(ts_dir / "load_24h.csv")
        bus_id_to_loads: dict[str, list] = {}
        for ld in loads:
            bus_id = ld.bus.code if hasattr(ld.bus, "code") else ld.bus.name
            bus_id_to_loads.setdefault(str(bus_id), []).append(ld)

        for _, row in load_df.iterrows():
            bus_id = str(int(row["bus_id"]))
            hourly_values = [row[f"HR_{h}"] for h in range(1, 25)]
            matched_loads = bus_id_to_loads.get(bus_id, [])
            for ld in matched_loads:
                profile_values = np.array(hourly_values, dtype=float)
                ld.P_prof.set(profile_values)

        results["details"]["load_profile_applied"] = True

        # 7. Configure and run time-series DCOPF
        opf_opts = vge.OptimalPowerFlowOptions(
            solver=SolverType.LINEAR_OPF,
            mip_solver=MIPSolvers.HIGHS,
        )

        time_indices = np.arange(n_hours)
        driver = OptimalPowerFlowTimeSeriesDriver(
            grid=grid,
            options=opf_opts,
            time_indices=time_indices,
        )
        driver.run()
        ts_results = driver.results

        if ts_results is None:
            results["errors"].append("OPF time series returned no results")
            return results

        # Check convergence
        conv_array = ts_results.converged
        converged = bool(np.all(conv_array))
        results["details"]["converged"] = converged
        n_converged = int(np.sum(conv_array))
        results["details"]["hours_converged"] = n_converged

        if not converged:
            results["details"]["converged_per_hour"] = conv_array.tolist()
            results["errors"].append(f"Not all hours converged: {n_converged}/{n_hours}")

        # 8. Extract results
        # All power/energy results from OPF TS are already in MW/MWh
        # (get_values() multiplies LP variables by Sbase)
        bus_shadow_prices = ts_results.bus_shadow_prices  # (nt, n_buses) — $/MWh
        gen_power = ts_results.generator_power  # (nt, n_gens) — MW
        batt_power = ts_results.battery_power  # (nt, n_batts) — MW
        batt_energy = ts_results.battery_energy  # (nt, n_batts) — MWh
        overloads = ts_results.overloads  # (nt, n_branches) — MW

        results["details"]["shapes"] = {
            "bus_shadow_prices": list(bus_shadow_prices.shape),
            "gen_power": list(gen_power.shape),
            "batt_power": list(batt_power.shape),
            "batt_energy": list(batt_energy.shape),
            "overloads": list(overloads.shape),
        }

        # =====================================================================
        # PASS CONDITION 1: Congestion reporting
        # =====================================================================
        [b.name for b in branches]

        shadow_threshold = 1e-6
        hours_with_congestion = 0
        congestion_by_hour = []

        for t in range(n_hours):
            nonzero_count = int(np.sum(np.abs(overloads[t, :]) > shadow_threshold))
            congestion_by_hour.append(nonzero_count)
            if nonzero_count >= 2:
                hours_with_congestion += 1

        results["details"]["congestion_by_hour"] = congestion_by_hour
        results["details"]["hours_with_ge2_congested_branches"] = hours_with_congestion

        shadow_mean_by_hour = np.mean(np.abs(overloads), axis=1).tolist()
        shadow_std_by_hour = np.std(np.abs(overloads), axis=1).tolist()
        results["details"]["shadow_price_mean_by_hour"] = [round(v, 4) for v in shadow_mean_by_hour]
        results["details"]["shadow_price_std_by_hour"] = [round(v, 4) for v in shadow_std_by_hour]

        pc1_pass = hours_with_congestion >= 2
        results["details"]["pc1_congestion_pass"] = pc1_pass

        # =====================================================================
        # PASS CONDITION 2: BESS arbitrage timing
        # =====================================================================
        bess_bus_idx = None
        for i, b in enumerate(buses):
            bus_code = b.code if hasattr(b, "code") else b.name
            if str(bus_code) == str(BESS_BUS_ID):
                bess_bus_idx = i
                break

        batt_p = batt_power[:, 0]  # MW; positive = discharge, negative = charge

        if bess_bus_idx is None:
            results["errors"].append(f"Could not find BESS bus index for bus {BESS_BUS_ID}")
            pc2_pass = False
        else:
            bess_lmps = bus_shadow_prices[:, bess_bus_idx]

            discharge_hours = np.where(batt_p > 0.01)[0]
            charge_hours = np.where(batt_p < -0.01)[0]

            results["details"]["bess_power_mw_by_hour"] = [round(float(v), 3) for v in batt_p]
            results["details"]["bess_lmp_by_hour"] = [round(float(v), 4) for v in bess_lmps]
            results["details"]["n_discharge_hours"] = len(discharge_hours)
            results["details"]["n_charge_hours"] = len(charge_hours)

            if len(discharge_hours) > 0 and len(charge_hours) > 0:
                mean_lmp_discharge = float(np.mean(bess_lmps[discharge_hours]))
                mean_lmp_charge = float(np.mean(bess_lmps[charge_hours]))
                results["details"]["mean_lmp_discharge"] = round(mean_lmp_discharge, 4)
                results["details"]["mean_lmp_charge"] = round(mean_lmp_charge, 4)
                pc2_pass = mean_lmp_discharge > mean_lmp_charge
                results["details"]["arbitrage_spread"] = round(
                    mean_lmp_discharge - mean_lmp_charge, 4
                )
            elif len(discharge_hours) == 0 and len(charge_hours) == 0:
                results["errors"].append("BESS did not charge or discharge (all |P| <= 0.01 MW)")
                pc2_pass = False
            else:
                results["errors"].append(
                    f"BESS only {'discharged' if len(discharge_hours) > 0 else 'charged'}"
                    f" ({len(discharge_hours)} discharge, {len(charge_hours)} charge hours). "
                    "Root cause: GridCal battery energy formulation has inverted sign "
                    "(E[t] = E[t-1] + eta_dis*P_dis*dt), causing energy to increase "
                    "during discharge. The optimizer sees discharge as free energy creation."
                )
                pc2_pass = False

        results["details"]["pc2_arbitrage_pass"] = pc2_pass

        # =====================================================================
        # PASS CONDITION 3: SoC feasibility
        # =====================================================================
        batt_e_mwh = batt_energy[:, 0]  # already in MWh

        results["details"]["bess_energy_mwh_by_hour"] = [round(float(v), 3) for v in batt_e_mwh]

        # SoC bounds check: SoC in [0, energy_capacity]
        soc_max_violation = max(0.0, float(np.max(batt_e_mwh)) - BESS_ENERGY_MWH)
        soc_min_violation = max(0.0, float(-np.min(batt_e_mwh)))
        soc_in_bounds = soc_max_violation <= 0.01 and soc_min_violation <= 0.01

        results["details"]["soc_min_mwh"] = round(float(np.min(batt_e_mwh)), 3)
        results["details"]["soc_max_mwh"] = round(float(np.max(batt_e_mwh)), 3)
        results["details"]["soc_in_bounds"] = soc_in_bounds

        # Energy balance: check with textbook convention first
        # |E[t] - E[t-1] + P_dis[t]*dt/eta_dis - P_ch[t]*dt*eta_ch| < 1.0 MWh
        dt = 1.0
        energy_balance_errors = []
        for t in range(1, n_hours):
            delta_e = batt_e_mwh[t] - batt_e_mwh[t - 1]
            p = batt_p[t]
            if p > 0.01:
                expected_delta = -p * dt / BESS_DISCHARGE_EFF
            elif p < -0.01:
                expected_delta = abs(p) * dt * BESS_CHARGE_EFF
            else:
                expected_delta = 0.0
            energy_balance_errors.append(abs(delta_e - expected_delta))

        max_balance_error = max(energy_balance_errors) if energy_balance_errors else 0.0
        mean_balance_error = float(np.mean(energy_balance_errors)) if energy_balance_errors else 0.0
        results["details"]["max_energy_balance_error_mwh"] = round(max_balance_error, 4)
        results["details"]["mean_energy_balance_error_mwh"] = round(mean_balance_error, 4)

        # Also check with GridCal's internal convention for reference
        energy_balance_errors_tool = []
        for t in range(1, n_hours):
            delta_e = batt_e_mwh[t] - batt_e_mwh[t - 1]
            p = batt_p[t]
            p_pos = max(p, 0)
            p_neg = max(-p, 0)
            expected_delta_tool = dt * (BESS_DISCHARGE_EFF * p_pos - BESS_CHARGE_EFF * p_neg)
            energy_balance_errors_tool.append(abs(delta_e - expected_delta_tool))

        max_balance_error_tool = (
            max(energy_balance_errors_tool) if energy_balance_errors_tool else 0.0
        )
        results["details"]["max_energy_balance_error_tool_convention_mwh"] = round(
            max_balance_error_tool, 4
        )
        results["details"]["tool_convention_note"] = (
            "GridCal linear_opf_ts.py line ~1776: "
            "E[t] = E[t-1] + dt*(eta_dis*p_pos - eta_ch*p_neg). "
            "When discharging (p_pos>0), energy INCREASES. "
            "Textbook convention: energy should DECREASE during discharge."
        )

        soc_feasible = soc_in_bounds and max_balance_error < 1.0
        results["details"]["pc3_soc_feasibility_pass"] = soc_feasible

        # =====================================================================
        # Overall pass determination
        # =====================================================================
        pass_checks = {
            "pc1_congestion": pc1_pass,
            "pc2_arbitrage": pc2_pass,
            "pc3_soc_feasibility": soc_feasible,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed pass conditions: {failing}")

        # Record additional diagnostics
        total_gen_by_hour = np.sum(gen_power, axis=1)
        results["details"]["total_generation_mw_by_hour"] = [
            round(float(v), 1) for v in total_gen_by_hour
        ]

        if bus_shadow_prices is not None and bus_shadow_prices.size > 0:
            results["details"]["lmp_min"] = round(float(np.min(bus_shadow_prices)), 4)
            results["details"]["lmp_max"] = round(float(np.max(bus_shadow_prices)), 4)
            results["details"]["lmp_mean"] = round(float(np.mean(bus_shadow_prices)), 4)

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
