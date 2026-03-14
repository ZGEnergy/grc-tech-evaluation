"""
Test A-12: Solve 24-hour multi-period DCOPF with storage and congestion on TINY (full Modified Tiny recipe)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, case39.m) -- Modified Tiny variant
Pass condition:
  (1) Congestion reporting: Mean and std of branch shadow prices computed by hour.
      At least 2 of 24 hours must have >=2 branches with non-zero shadow prices.
  (2) BESS arbitrage timing: Mean LMP at the BESS bus during discharge hours (P > 0.01 MW)
      must exceed mean LMP during charge hours (P < -0.01 MW). Hours with |P| <= 0.01 MW
      are excluded.
  (3) SoC feasibility: SoC in [0, energy_capacity] at all timesteps, AND energy balance
      trajectory consistent: |SoC[t] - SoC[t-1] - eta_ch*P_ch[t] + P_dis[t]/eta_dis|
      < 1.0 MWh for each t (dt=1h).
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
DEFAULT_TIMESERIES = str(REPO_ROOT / "data" / "timeseries" / "case39")

# Solver configuration (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300.0,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

# Cost mapping from gen_temporal_params.csv tech_class_key (README recipe)
COST_MAP = {
    "hydro": 5.0,
    "nuclear": 10.0,
    "coal_large": 25.0,
    "gas_CC": 40.0,
}

# Quadratic coefficient: c2 = c1 * 0.001 (README recipe)
C2_FACTOR = 0.001

# Branch derating factor (README recipe: 70%)
BRANCH_DERATE = 0.70

# BESS parameters from test spec (not bess_units.csv -- test spec overrides)
BESS_BUS = "16"
BESS_P_NOM = 50.0  # MW
BESS_ENERGY = 200.0  # MWh (50 MW * 4h)
BESS_MAX_HOURS = 4.0  # energy/power ratio
BESS_ETA_CHARGE = 0.92
BESS_ETA_DISCHARGE = 0.95


def load_modified_tiny(network_file: str, timeseries_dir: str) -> object:
    """Load case39.m and apply the full Modified Tiny recipe per the README."""
    from matpower_loader import load_pypsa

    ts_dir = Path(timeseries_dir)

    # 1. Load base network via shared loader (applies transformer b-fix + gencost)
    n = load_pypsa(network_file)

    # 2. Set 24-hour snapshots
    snapshots = pd.date_range("2024-01-01 00:00", periods=24, freq="h")
    n.set_snapshots(snapshots)

    # 3. Replace generator costs with differentiated costs from gen_temporal_params.csv
    gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")
    gen_names = n.generators.index.tolist()

    for _, row in gen_params.iterrows():
        gen_idx = int(row["gen_index"])
        if gen_idx < len(gen_names):
            gen_name = gen_names[gen_idx]
            tech_key = row["tech_class_key"]
            c1 = COST_MAP.get(tech_key, 30.0)
            c2 = c1 * C2_FACTOR
            n.generators.at[gen_name, "marginal_cost"] = c1
            n.generators.at[gen_name, "marginal_cost_quadratic"] = c2

    # 4. Load time-varying demand from load_24h.csv
    load_df = pd.read_csv(ts_dir / "load_24h.csv", index_col="bus_id")
    # load_df has columns HR_1..HR_24, rows are bus_ids
    for load_name in n.loads.index:
        # Load names from pypower import are like "L0", "L1", etc.
        # The bus they're attached to is n.loads.at[load_name, "bus"]
        bus_str = str(n.loads.at[load_name, "bus"])
        bus_id = int(bus_str)
        if bus_id in load_df.index:
            hourly_mw = load_df.loc[bus_id, [f"HR_{h}" for h in range(1, 25)]].values.astype(float)
            n.loads_t.p_set[load_name] = hourly_mw

    # 5. Derate all branch ratings to 70%
    n.lines["s_nom"] = n.lines["s_nom"] * BRANCH_DERATE
    if len(n.transformers) > 0:
        n.transformers["s_nom"] = n.transformers["s_nom"] * BRANCH_DERATE

    # 6. Add BESS at bus 16 per test spec
    n.add(
        "StorageUnit",
        "BESS",
        bus=BESS_BUS,
        p_nom=BESS_P_NOM,
        max_hours=BESS_MAX_HOURS,
        efficiency_store=BESS_ETA_CHARGE,
        efficiency_dispatch=BESS_ETA_DISCHARGE,
        cyclic_state_of_charge=True,
        marginal_cost=0.0,
        carrier="battery",
    )

    return n


def run(
    network_file: str = DEFAULT_NETWORK,
    timeseries_dir: str | None = None,
) -> dict:
    """Execute 24-hour multi-period DCOPF with storage on Modified Tiny.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    if timeseries_dir is None:
        timeseries_dir = DEFAULT_TIMESERIES

    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import tracemalloc

        tracemalloc.start()

        # 1. Load and configure Modified Tiny network
        n = load_modified_tiny(network_file, timeseries_dir)

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["n_storage_units"] = len(n.storage_units)
        results["details"]["n_snapshots"] = len(n.snapshots)
        results["details"]["branch_derate_factor"] = BRANCH_DERATE

        # 2. Solve multi-period DCOPF
        solve_start = time.perf_counter()
        opf_status, opf_condition = n.optimize(
            snapshots=n.snapshots,
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        solve_elapsed = time.perf_counter() - solve_start

        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["details"]["peak_memory_mb"] = round(peak_mem / (1024 * 1024), 2)

        results["details"]["solve_seconds"] = round(solve_elapsed, 4)
        results["details"]["solver_status"] = str(opf_status)
        results["details"]["solver_condition"] = str(opf_condition)
        results["details"]["objective_value"] = float(n.objective)

        if str(opf_status).lower() not in ("ok", "optimal"):
            results["errors"].append(f"OPF failed: {opf_status}, {opf_condition}")
            return results

        print(f"Multi-period OPF solved: objective=${n.objective:,.2f}")
        print(f"  Solve time: {solve_elapsed:.3f}s")

        # 3. Extract results

        # --- LMPs ---
        lmps = n.buses_t.marginal_price  # [24, n_buses]
        results["details"]["lmp_mean"] = round(float(lmps.values.mean()), 4)
        results["details"]["lmp_min"] = round(float(lmps.values.min()), 4)
        results["details"]["lmp_max"] = round(float(lmps.values.max()), 4)

        # --- Branch shadow prices ---
        # PyPSA populates n.lines_t.mu_lower and n.lines_t.mu_upper after optimize()
        mu_upper = n.lines_t.mu_upper if len(n.lines_t.mu_upper) > 0 else pd.DataFrame()
        mu_lower = n.lines_t.mu_lower if len(n.lines_t.mu_lower) > 0 else pd.DataFrame()

        # Combine: shadow price magnitude per line per hour
        shadow_abs = pd.DataFrame(0.0, index=n.snapshots, columns=n.lines.index)
        if len(mu_upper) > 0:
            shadow_abs = shadow_abs.add(mu_upper.abs(), fill_value=0.0)
        if len(mu_lower) > 0:
            shadow_abs = shadow_abs.add(mu_lower.abs(), fill_value=0.0)

        # If mu_upper/mu_lower are empty, try linopy model duals as fallback
        mu_populated = shadow_abs.abs().sum().sum() > 1e-8
        shadow_extraction_method = "mu_upper_mu_lower"

        if not mu_populated:
            shadow_extraction_method = "linopy_model_duals"
            results["workarounds"].append(
                "n.lines_t.mu_upper/mu_lower empty after n.optimize() in PyPSA v1.1.2; "
                "extracted branch shadow prices from linopy model constraint duals "
                "(n.model.constraints['Line-fix-s-upper'].dual). Classification: fragile "
                "(depends on internal constraint naming convention)."
            )
            try:
                if hasattr(n, "model") and n.model is not None:
                    for cname in ["Line-fix-s-upper", "Line-fix-s-lower"]:
                        if cname in n.model.constraints:
                            dual_da = n.model.constraints[cname].dual
                            if dual_da is not None:
                                dual_df = dual_da.to_pandas()
                                if isinstance(dual_df, pd.DataFrame):
                                    shadow_abs = shadow_abs.add(dual_df.abs(), fill_value=0.0)
                    mu_populated = shadow_abs.abs().sum().sum() > 1e-8
            except Exception as e:
                results["details"]["shadow_fallback_error"] = str(e)

        results["details"]["shadow_extraction_method"] = shadow_extraction_method
        results["details"]["shadow_prices_populated"] = mu_populated

        # Compute hourly shadow price statistics
        n_nonzero_branches_per_hour = (shadow_abs > 1e-6).sum(axis=1)
        shadow_mean_per_hour = shadow_abs.mean(axis=1)
        shadow_std_per_hour = shadow_abs.std(axis=1)

        results["details"]["shadow_mean_by_hour"] = {
            f"h{i:02d}": round(float(v), 4) for i, v in enumerate(shadow_mean_per_hour)
        }
        results["details"]["shadow_std_by_hour"] = {
            f"h{i:02d}": round(float(v), 4) for i, v in enumerate(shadow_std_per_hour)
        }
        results["details"]["n_nonzero_branches_per_hour"] = {
            f"h{i:02d}": int(v) for i, v in enumerate(n_nonzero_branches_per_hour)
        }

        # Pass condition 1: At least 2 hours with >=2 branches having non-zero shadow prices
        hours_with_2plus_binding = int((n_nonzero_branches_per_hour >= 2).sum())
        cond1_pass = hours_with_2plus_binding >= 2
        results["details"]["hours_with_ge2_binding_branches"] = hours_with_2plus_binding
        results["details"]["cond1_congestion_pass"] = cond1_pass

        print("\n=== Congestion (Pass Condition 1) ===")
        print(f"  Hours with >=2 binding branches: {hours_with_2plus_binding}/24")
        print(f"  Condition 1 pass: {cond1_pass}")

        # --- BESS dispatch and arbitrage ---
        bess_p = n.storage_units_t.p["BESS"]  # positive=discharge, negative=charge in PyPSA
        bess_soc = n.storage_units_t.state_of_charge["BESS"]
        bess_bus = BESS_BUS

        # LMP at BESS bus
        lmp_bess = lmps[bess_bus]

        # Identify charge/discharge hours (threshold: 0.01 MW)
        discharge_mask = bess_p > 0.01
        charge_mask = bess_p < -0.01

        n_discharge_hours = int(discharge_mask.sum())
        n_charge_hours = int(charge_mask.sum())

        results["details"]["bess_dispatch_by_hour"] = {
            f"h{i:02d}": round(float(v), 4) for i, v in enumerate(bess_p)
        }
        results["details"]["bess_soc_by_hour"] = {
            f"h{i:02d}": round(float(v), 4) for i, v in enumerate(bess_soc)
        }
        results["details"]["bess_n_discharge_hours"] = n_discharge_hours
        results["details"]["bess_n_charge_hours"] = n_charge_hours
        results["details"]["bess_total_discharge_mwh"] = round(
            float(bess_p[discharge_mask].sum()), 4
        )
        results["details"]["bess_total_charge_mwh"] = round(
            float(bess_p[charge_mask].abs().sum()), 4
        )

        # Pass condition 2: mean LMP during discharge > mean LMP during charge
        if n_discharge_hours > 0 and n_charge_hours > 0:
            mean_lmp_discharge = float(lmp_bess[discharge_mask].mean())
            mean_lmp_charge = float(lmp_bess[charge_mask].mean())
            cond2_pass = mean_lmp_discharge > mean_lmp_charge
            results["details"]["mean_lmp_discharge"] = round(mean_lmp_discharge, 4)
            results["details"]["mean_lmp_charge"] = round(mean_lmp_charge, 4)
        else:
            cond2_pass = False
            mean_lmp_discharge = None
            mean_lmp_charge = None
            results["details"]["mean_lmp_discharge"] = None
            results["details"]["mean_lmp_charge"] = None
            results["details"]["cond2_note"] = (
                f"Insufficient BESS activity: {n_discharge_hours} discharge hours, "
                f"{n_charge_hours} charge hours"
            )

        results["details"]["cond2_arbitrage_pass"] = cond2_pass

        print("\n=== BESS Arbitrage (Pass Condition 2) ===")
        print(f"  Discharge hours: {n_discharge_hours}, Charge hours: {n_charge_hours}")
        print(f"  Mean LMP during discharge: {mean_lmp_discharge}")
        print(f"  Mean LMP during charge: {mean_lmp_charge}")
        print(f"  Condition 2 pass: {cond2_pass}")

        # --- SoC feasibility (Pass Condition 3) ---
        energy_capacity = BESS_P_NOM * BESS_MAX_HOURS  # 200 MWh

        # Check SoC bounds: [0, energy_capacity]
        soc_min = float(bess_soc.min())
        soc_max = float(bess_soc.max())
        soc_in_bounds = (soc_min >= -1e-6) and (soc_max <= energy_capacity + 1e-6)

        # Check energy balance trajectory consistency
        # |SoC[t] - SoC[t-1] - eta_ch*P_ch[t] + P_dis[t]/eta_dis| < 1.0 MWh
        # PyPSA sign: positive P = discharge, negative P = charge
        # P_ch[t] = max(0, -bess_p[t])  (charge power, positive when charging)
        # P_dis[t] = max(0, bess_p[t])  (discharge power, positive when discharging)
        soc_vals = bess_soc.values
        p_vals = bess_p.values

        energy_balance_errors = []
        for t in range(len(soc_vals)):
            if t == 0:
                # For cyclic SoC, SoC[-1] = SoC[23]
                soc_prev = soc_vals[-1]
            else:
                soc_prev = soc_vals[t - 1]

            p_ch = max(0.0, -p_vals[t])  # charge power (MW)
            p_dis = max(0.0, p_vals[t])  # discharge power (MW)

            # Expected SoC change: +eta_ch*P_ch - P_dis/eta_dis (dt=1h)
            expected_delta = BESS_ETA_CHARGE * p_ch - p_dis / BESS_ETA_DISCHARGE
            actual_delta = soc_vals[t] - soc_prev
            error = abs(actual_delta - expected_delta)
            energy_balance_errors.append(error)

        max_balance_error = max(energy_balance_errors)
        balance_consistent = all(e < 1.0 for e in energy_balance_errors)

        cond3_pass = soc_in_bounds and balance_consistent

        results["details"]["soc_min_mwh"] = round(soc_min, 4)
        results["details"]["soc_max_mwh"] = round(soc_max, 4)
        results["details"]["energy_capacity_mwh"] = energy_capacity
        results["details"]["soc_in_bounds"] = soc_in_bounds
        results["details"]["max_energy_balance_error_mwh"] = round(max_balance_error, 6)
        results["details"]["energy_balance_consistent"] = balance_consistent
        results["details"]["cond3_soc_pass"] = cond3_pass

        print("\n=== SoC Feasibility (Pass Condition 3) ===")
        print(f"  SoC range: [{soc_min:.2f}, {soc_max:.2f}] MWh (capacity: {energy_capacity})")
        print(f"  SoC in bounds: {soc_in_bounds}")
        print(f"  Max energy balance error: {max_balance_error:.6f} MWh (threshold: 1.0)")
        print(f"  Balance consistent: {balance_consistent}")
        print(f"  Condition 3 pass: {cond3_pass}")

        # --- Hourly dispatch summary ---
        gen_dispatch = n.generators_t.p
        load_by_hour = n.loads_t.p_set.sum(axis=1)

        dispatch_summary = []
        for i, snap in enumerate(n.snapshots):
            dispatch_summary.append(
                {
                    "hour": i,
                    "load_mw": round(float(load_by_hour.iloc[i]), 2),
                    "total_gen_mw": round(float(gen_dispatch.iloc[i].sum()), 2),
                    "bess_mw": round(float(bess_p.iloc[i]), 2),
                    "bess_soc_mwh": round(float(bess_soc.iloc[i]), 2),
                    "lmp_bess_bus": round(float(lmp_bess.iloc[i]), 4),
                    "mean_lmp": round(float(lmps.iloc[i].mean()), 4),
                    "n_binding_branches": int(n_nonzero_branches_per_hour.iloc[i]),
                }
            )
        results["details"]["hourly_dispatch"] = dispatch_summary

        print("\n=== Hourly Dispatch Summary ===")
        print(
            f"{'Hr':>3} {'Load':>8} {'GenTot':>8} {'BESS':>7} {'SoC':>7} {'LMP-16':>8} {'Bind':>5}"
        )
        for row in dispatch_summary:
            print(
                f"{row['hour']:>3} {row['load_mw']:>8.1f} {row['total_gen_mw']:>8.1f} "
                f"{row['bess_mw']:>7.1f} {row['bess_soc_mwh']:>7.1f} "
                f"{row['lmp_bess_bus']:>8.2f} {row['n_binding_branches']:>5}"
            )

        # --- Overall pass/fail ---
        all_pass = cond1_pass and cond2_pass and cond3_pass
        results["details"]["pass_conditions"] = {
            "cond1_congestion": cond1_pass,
            "cond2_arbitrage": cond2_pass,
            "cond3_soc_feasibility": cond3_pass,
        }

        if all_pass:
            results["status"] = "pass"
        else:
            failing = [k for k, v in results["details"]["pass_conditions"].items() if not v]
            results["errors"].append(f"Pass condition(s) not met: {failing}")

        print(f"\n=== Final Result: {results['status'].upper()} ===")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 4)

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
