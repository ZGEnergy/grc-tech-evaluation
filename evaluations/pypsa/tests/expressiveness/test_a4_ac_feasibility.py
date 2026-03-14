"""
Test A-4: AC Feasibility Check (ac_feasibility)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Achievable within the same model context (no export to file and reimport).
  Voltage violations and thermal limit violations identifiable from results.
Solver: Ipopt
Tool: PyPSA 1.1.2

Depends on: A-3 (DC OPF dispatch)
"""

import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")
DEFAULT_TIMESERIES = str(REPO_ROOT / "data" / "timeseries" / "case39")

# Voltage violation limits (per unit)
V_MIN_PU = 0.95
V_MAX_PU = 1.05

# Solver configuration for DC OPF (per solver-config.md)
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

# Cost map from Modified Tiny data
COST_MAP = {
    "hydro": 5.0,
    "nuclear": 10.0,
    "coal_large": 25.0,
    "gas_CC": 40.0,
}


def run(
    network_file: str = DEFAULT_NETWORK,
    timeseries_dir: str | None = DEFAULT_TIMESERIES,
) -> dict:
    """Execute AC feasibility check on DC OPF dispatch from A-3.

    Methodology:
    1. Load network with A-3 setup (differentiated costs + 70% branch derating)
    2. Solve DC OPF to obtain dispatch (reproducing A-3 within same model context)
    3. Fix generator dispatch to DC OPF values via generators_t.p_set
    4. Run n.pf() (Newton-Raphson AC power flow) with flat start
    5. Verify convergence quality per convergence-protocol.md
    6. Check voltage violations (outside [0.95, 1.05] pu)
    7. Check thermal limit violations (|flow| > s_nom)

    Returns:
        dict with standard keys (status, wall_clock_seconds, details, errors, workarounds)
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
        import pypsa
        from matpowercaseframes import CaseFrames

        # Helper: load network WITHOUT the DC transformer susceptance patch
        # (the shared loader applies b=1/x for DC, which breaks AC PF)
        def load_raw(fpath):
            cf = CaseFrames(str(fpath))
            ppc = {
                "version": "2",
                "baseMVA": float(cf.baseMVA),
                "bus": cf.bus.values,
                "gen": cf.gen.values,
                "branch": cf.branch.values,
            }
            net = pypsa.Network()
            net.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
            return net

        # 1. Load network via shared loader (WITH DC patch) for DC OPF
        from matpower_loader import load_pypsa

        n = load_pypsa(network_file)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        results["details"]["n_generators"] = len(n.generators)

        base_mva = 100.0  # case39 baseMVA
        results["details"]["base_mva"] = base_mva

        # 2. Apply Modified Tiny: differentiated costs + 70% branch derating (same as A-3)
        if timeseries_dir is None:
            results["errors"].append("timeseries_dir is required for Modified Tiny data")
            return results

        ts_dir = Path(timeseries_dir)
        gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")
        gen_names = n.generators.index.tolist()

        for _, row in gen_params.iterrows():
            gen_idx = int(row["gen_index"])
            tech_key = row["tech_class_key"]
            if gen_idx < len(gen_names):
                gen_name = gen_names[gen_idx]
                mc = COST_MAP.get(tech_key, 30.0)
                n.generators.at[gen_name, "marginal_cost"] = mc

        # 70% branch derating (same as A-3)
        n.lines.s_nom = n.lines.s_nom * 0.7
        if len(n.transformers) > 0:
            n.transformers.s_nom = n.transformers.s_nom * 0.7
        results["details"]["branch_derating"] = "70% (same as A-3)"

        # 3. Solve DC OPF (reproducing A-3 within same model context)
        dcopf_status, dcopf_condition = n.optimize(
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        results["details"]["dcopf_status"] = str(dcopf_status)
        results["details"]["dcopf_condition"] = str(dcopf_condition)
        results["details"]["dcopf_objective"] = float(n.objective)

        if str(dcopf_status).lower() not in ("ok", "optimal"):
            results["errors"].append(f"DC OPF failed: {dcopf_status}, {dcopf_condition}")
            return results

        # Extract DC OPF dispatch
        dc_dispatch = n.generators_t.p.iloc[0].to_dict()
        results["details"]["dc_dispatch_mw"] = dc_dispatch
        results["details"]["total_dc_dispatch_mw"] = float(sum(dc_dispatch.values()))
        print("=== DC OPF Dispatch (MW) ===")
        for gen, mw in dc_dispatch.items():
            print(f"  {gen}: {mw:.1f} MW")

        # Log unit consistency at transfer point
        results["details"]["unit_check"] = {
            "base_power_mva": base_mva,
            "dispatch_units": "MW",
            "line_limit_units": "MVA (s_nom after 70% derating)",
            "pf_dispatch_units": "MW (p_set)",
        }

        # 4. Fix generator dispatch for AC power flow
        # Load network WITHOUT DC patch for AC PF (the shared loader's transformer
        # susceptance patch b=1/x is specific to DC convention and causes AC PF
        # divergence — see A-2 result which documents this)
        n_fresh = load_raw(network_file)

        # Note: We check thermal violations against the DERATED limits (70%) since
        # the DC OPF was solved with those limits. AC PF may show additional
        # violations because AC flow includes reactive power (apparent power > active).

        # Set generator active power dispatch from DC OPF results
        snapshot = n_fresh.snapshots[0]
        p_set_df = pd.DataFrame(dc_dispatch, index=[snapshot])
        n_fresh.generators_t.p_set = p_set_df

        results["details"]["same_model_context"] = True
        results["details"]["generators_dispatched"] = len(dc_dispatch)

        # 5. Run Newton-Raphson AC power flow (flat start)
        # converges_ac: true per test definition
        print("\n=== Running AC Power Flow (flat start) ===")
        pf_start = time.perf_counter()
        pf_result = n_fresh.pf(snapshots=[snapshot])
        pf_elapsed = time.perf_counter() - pf_start
        results["details"]["pf_wall_clock_seconds"] = pf_elapsed

        # Extract convergence info
        converged = False
        n_iterations = None
        convergence_residual = None

        if isinstance(pf_result, dict):
            if "converged" in pf_result:
                converged_df = pf_result["converged"]
                converged = bool(converged_df.values.flatten()[0])
            if "n_iter" in pf_result:
                n_iter_df = pf_result["n_iter"]
                n_iterations = int(n_iter_df.values.flatten()[0])
            if "error" in pf_result:
                error_df = pf_result["error"]
                convergence_residual = float(error_df.values.flatten()[0])

        results["details"]["pf_converged"] = converged
        results["details"]["pf_iterations"] = n_iterations
        results["details"]["convergence_residual"] = convergence_residual

        print(
            f"  Converged: {converged}, Iterations: {n_iterations}, "
            f"Residual: {convergence_residual}"
        )

        if not converged:
            # DC warm start fallback (per convergence-protocol.md)
            print("\n=== Flat start failed — attempting DC warm start ===")
            n_warm = load_raw(network_file)

            # Run DCPF first for angle initialization
            n_warm.lpf()
            dc_angles = n_warm.buses_t.v_ang.iloc[0] if len(n_warm.buses_t.v_ang) > 0 else None

            # Set dispatch and warm-start angles
            n_warm.generators_t.p_set = p_set_df
            if dc_angles is not None:
                for bus in n_warm.buses.index:
                    n_warm.buses.at[bus, "v_ang"] = float(dc_angles.get(bus, 0.0))

            pf_start2 = time.perf_counter()
            pf_result2 = n_warm.pf(snapshots=[snapshot], use_seed=True)
            pf_elapsed2 = time.perf_counter() - pf_start2

            if isinstance(pf_result2, dict) and "converged" in pf_result2:
                converged = bool(pf_result2["converged"].values.flatten()[0])
            if isinstance(pf_result2, dict) and "n_iter" in pf_result2:
                n_iterations = int(pf_result2["n_iter"].values.flatten()[0])
            if isinstance(pf_result2, dict) and "error" in pf_result2:
                convergence_residual = float(pf_result2["error"].values.flatten()[0])

            results["details"]["dc_warm_start_used"] = True
            results["details"]["pf_converged"] = converged
            results["details"]["pf_iterations"] = n_iterations
            results["details"]["convergence_residual"] = convergence_residual
            results["details"]["pf_wall_clock_seconds"] = pf_elapsed + pf_elapsed2

            n_fresh = n_warm
            print(
                f"  DC warm start: converged={converged}, iter={n_iterations}, "
                f"residual={convergence_residual}"
            )

        if not converged:
            results["errors"].append("AC power flow did not converge (flat start + DC warm start)")
            results["status"] = "fail"
            return results

        # 6. Convergence quality checks (per convergence-protocol.md)
        v_mag = n_fresh.buses_t.v_mag_pu
        if len(v_mag) == 0:
            results["errors"].append("v_mag_pu is empty after pf()")
            return results

        v_vals = v_mag.iloc[0]
        n_buses_total = len(v_vals)
        n_flat = int((np.abs(v_vals - 1.0) < 1e-6).sum())
        frac_nontrivial = 1.0 - (n_flat / n_buses_total)
        results["details"]["frac_buses_nontrivial_voltage"] = float(frac_nontrivial)

        if frac_nontrivial < 0.95:
            results["details"]["convergence_quality_warning"] = (
                f"Only {frac_nontrivial:.1%} of buses have non-flat-start voltages "
                f"(< 95% threshold). May be trivial solution."
            )

        # Iteration count > 0 check
        if n_iterations is not None and n_iterations == 0:
            results["details"]["convergence_quality_warning"] = (
                "Zero NR iterations — solver may not have actually run."
            )

        # 7. Check voltage violations (outside [0.95, 1.05] pu)
        v_violations = []
        for bus_name in v_vals.index:
            v = float(v_vals[bus_name])
            if v < V_MIN_PU or v > V_MAX_PU:
                v_violations.append(
                    {
                        "bus": bus_name,
                        "v_mag_pu": round(v, 5),
                        "violation": "low" if v < V_MIN_PU else "high",
                        "margin_pu": round(
                            float(v - V_MIN_PU if v < V_MIN_PU else v - V_MAX_PU), 5
                        ),
                    }
                )

        results["details"]["voltage_violations"] = v_violations
        results["details"]["n_voltage_violations"] = len(v_violations)
        results["details"]["v_min_pu"] = float(v_vals.min())
        results["details"]["v_max_pu"] = float(v_vals.max())

        print("\n=== Voltage Profile ===")
        print(f"  Min: {v_vals.min():.5f} pu, Max: {v_vals.max():.5f} pu")
        print(f"  Violations outside [{V_MIN_PU}, {V_MAX_PU}]: {len(v_violations)}")
        for vv in v_violations[:10]:
            print(f"    Bus {vv['bus']}: {vv['v_mag_pu']:.5f} pu ({vv['violation']})")

        # 8. Check thermal limit violations (|S| > s_nom)
        # Use the derated s_nom (70%) since that was the DC OPF constraint set
        thermal_violations = []

        # Lines — check against 70% derated limits
        p0_lines = n_fresh.lines_t.p0
        q0_lines = n_fresh.lines_t.q0
        derated_s_nom_lines = n.lines.s_nom  # from the derated network

        if len(p0_lines) > 0:
            p0_vals = p0_lines.iloc[0]
            q0_vals = q0_lines.iloc[0] if len(q0_lines) > 0 else pd.Series(0, index=p0_vals.index)
            s_vals = np.sqrt(p0_vals**2 + q0_vals**2)  # apparent power

            for line_name in s_vals.index:
                flow_mva = float(s_vals[line_name])
                limit_mva = float(derated_s_nom_lines.get(line_name, 0))
                if limit_mva > 0 and flow_mva > limit_mva:
                    thermal_violations.append(
                        {
                            "branch": line_name,
                            "type": "line",
                            "flow_mva": round(flow_mva, 2),
                            "limit_mva": round(limit_mva, 2),
                            "loading_pct": round(flow_mva / limit_mva * 100, 1),
                        }
                    )

        # Transformers
        p0_xfmr = n_fresh.transformers_t.p0
        q0_xfmr = n_fresh.transformers_t.q0
        derated_s_nom_xfmr = n.transformers.s_nom if len(n.transformers) > 0 else pd.Series()

        if len(p0_xfmr) > 0:
            p0_xvals = p0_xfmr.iloc[0]
            q0_xvals = q0_xfmr.iloc[0] if len(q0_xfmr) > 0 else pd.Series(0, index=p0_xvals.index)
            s_xvals = np.sqrt(p0_xvals**2 + q0_xvals**2)

            for xfmr_name in s_xvals.index:
                flow_mva = float(s_xvals[xfmr_name])
                limit_mva = float(derated_s_nom_xfmr.get(xfmr_name, 0))
                if limit_mva > 0 and flow_mva > limit_mva:
                    thermal_violations.append(
                        {
                            "branch": xfmr_name,
                            "type": "transformer",
                            "flow_mva": round(flow_mva, 2),
                            "limit_mva": round(limit_mva, 2),
                            "loading_pct": round(flow_mva / limit_mva * 100, 1),
                        }
                    )

        results["details"]["thermal_violations"] = thermal_violations
        results["details"]["n_thermal_violations"] = len(thermal_violations)

        print("\n=== Thermal Limit Violations (vs 70% derated limits) ===")
        print(f"  Total: {len(thermal_violations)}")
        for tv in thermal_violations[:10]:
            print(
                f"    {tv['type'].capitalize()} {tv['branch']}: "
                f"{tv['flow_mva']:.1f} MVA > {tv['limit_mva']:.1f} MVA "
                f"({tv['loading_pct']:.1f}%)"
            )

        # 9. Check reactive power limit violations
        q_gen = n_fresh.generators_t.q
        q_violations = []
        if len(q_gen) > 0:
            q_vals = q_gen.iloc[0]
            for gen_name in q_vals.index:
                q_mw = float(q_vals[gen_name])
                # Report but don't fail — reactive power limits may not be modeled
                q_violations.append({"generator": gen_name, "q_mvar": round(q_mw, 2)})
        results["details"]["reactive_power_mvar"] = q_violations

        # 10. Summary
        results["details"]["pf_summary"] = {
            "converged": converged,
            "iterations": n_iterations,
            "residual": convergence_residual,
            "n_voltage_violations": len(v_violations),
            "n_thermal_violations": len(thermal_violations),
            "v_min_pu": float(v_vals.min()),
            "v_max_pu": float(v_vals.max()),
            "same_model_context": True,
        }

        # 11. Pass condition:
        # "Achievable within the same model context (no export to file and reimport).
        #  Voltage violations and thermal limit violations identifiable from results."
        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
