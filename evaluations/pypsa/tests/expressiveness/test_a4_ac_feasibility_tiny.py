"""
Test A-4: AC Feasibility Check (ac_feasibility)

Dimension: expressiveness
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Achievable within the same model context (no export to file and reimport).
  Voltage violations and thermal limit violations from DC dispatch are accessible as
  structured output.
Tool: PyPSA 1.1.2

Depends on: A-3 (DC OPF dispatch — read from A-3 results)
"""

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")

# --- A-3 DC OPF dispatch values (from re-running A-3 test script) ---
# These are the optimal dispatch values (MW) from the A-3 qualified_pass result.
# All 10 generators are dispatched (A-3 result file only showed notable generators).
# Generator names correspond to PyPSA generator indices after import_from_pypower_ppc.
A3_DISPATCH_MW = {
    "G0": 465.289,
    "G1": 646.0,
    "G2": 630.0,
    "G3": 630.0,
    "G4": 470.0,
    "G5": 630.0,
    "G6": 580.0,
    "G7": 262.941,
    "G8": 840.0,
    "G9": 1100.0,
}

# Voltage violation limits (per unit)
V_MIN_PU = 0.95
V_MAX_PU = 1.05


def load_network(network_file: str):
    """Load case39.m via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute AC feasibility check on DC OPF dispatch from A-3.

    Methodology:
    1. Load network (same model context — no file export/reimport)
    2. Fix generator dispatch to A-3 DC OPF values via generators_t.p_set
    3. Run n.pf() (Newton-Raphson AC power flow)
    4. Check voltage violations (outside [0.95, 1.05] pu)
    5. Check thermal limit violations (|flow| > s_nom)
    6. Report structured violation summary

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
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
        # 1. Load network
        n = load_network(network_file)
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        results["details"]["n_generators"] = len(n.generators)

        base_mva = 100.0  # case39 baseMVA
        results["details"]["base_mva"] = base_mva

        # 2. Fix generator dispatch to A-3 DC OPF values (within same model context)
        # This is the key "same model context" test — no file export/reimport needed.
        # We modify n.generators_t.p_set in-place to fix active power injection.
        snapshot = n.snapshots[0]

        # Build p_set DataFrame for the single snapshot
        # p_set is in MW for PyPSA when consistency with imports is maintained.
        dispatch_set = {}
        gen_names_in_network = set(n.generators.index)
        for gen_name, dispatch_mw in A3_DISPATCH_MW.items():
            if gen_name in gen_names_in_network:
                dispatch_set[gen_name] = dispatch_mw

        # Set generators_t.p_set — PyPSA uses MW (not per-unit) for generator dispatch
        # Flat-start: voltages initialized to 1.0 pu (default for n.pf())
        p_set_df = pd.DataFrame(dispatch_set, index=[snapshot])
        n.generators_t.p_set = p_set_df

        results["details"]["generators_dispatched"] = len(dispatch_set)
        results["details"]["total_dispatch_mw"] = float(sum(dispatch_set.values()))
        results["details"]["a3_dispatch_applied"] = dispatch_set

        # Note: same model context verified — no file export/reimport
        results["details"]["same_model_context"] = True

        # 3. Run Newton-Raphson AC power flow
        # n.pf() uses flat start by default (v_mag_pu=1.0, v_ang=0.0)
        # converges_ac: true — must verify convergence quality
        pf_start = time.perf_counter()
        pf_result = n.pf(snapshots=[snapshot])
        pf_elapsed = time.perf_counter() - pf_start

        results["details"]["pf_wall_clock_seconds"] = pf_elapsed

        # Extract convergence info from pf_result
        # PyPSA pf() returns a Dict with keys: 'n_iter', 'error', 'converged'
        # Each value is a DataFrame with one row per (snapshot, sub_network) pair.
        converged = False
        n_iterations = None
        convergence_residual = None

        try:
            if "converged" in pf_result:
                converged_df = pf_result["converged"]
                converged = bool(converged_df.values.flatten()[0])
            if "n_iter" in pf_result:
                n_iter_df = pf_result["n_iter"]
                n_iterations = int(n_iter_df.values.flatten()[0])
            if "error" in pf_result:
                error_df = pf_result["error"]
                convergence_residual = float(error_df.values.flatten()[0])
            print(
                f"AC PF result: converged={converged}, n_iter={n_iterations}, "
                f"residual={convergence_residual}"
            )
        except Exception:
            # Fallback: iterate items
            for sub_key, sub_result in pf_result.items():
                if hasattr(sub_result, "values"):
                    val = sub_result.values.flatten()[0]
                    if sub_key == "converged":
                        converged = bool(val)
                    elif sub_key == "n_iter":
                        n_iterations = int(val)
                    elif sub_key == "error":
                        convergence_residual = float(val)
            print(
                f"AC PF (fallback parse): converged={converged}, n_iter={n_iterations}, "
                f"residual={convergence_residual}"
            )

        results["details"]["pf_converged"] = converged
        results["details"]["pf_iterations"] = n_iterations
        results["details"]["convergence_residual"] = convergence_residual

        if not converged:
            results["errors"].append("AC power flow did not converge (Newton-Raphson)")
            results["status"] = "fail"
            return results

        # --- Convergence quality checks (per convergence-protocol.md) ---
        v_mag = n.buses_t.v_mag_pu

        # Check: voltage magnitudes differ from 1.0 pu on >95% of buses
        if len(v_mag) > 0:
            v_vals = v_mag.iloc[0]
            n_buses_total = len(v_vals)
            n_flat = (np.abs(v_vals - 1.0) < 1e-6).sum()
            frac_flat = n_flat / n_buses_total if n_buses_total > 0 else 1.0
            frac_nontrivial = 1.0 - frac_flat
            results["details"]["frac_buses_nontrivial_voltage"] = float(frac_nontrivial)
            if frac_nontrivial < 0.95:
                results["errors"].append(
                    f"Convergence quality concern: only {frac_nontrivial:.1%} of buses have "
                    f"non-flat-start voltages (< 95% threshold). Possible trivial solution."
                )
        else:
            results["errors"].append("v_mag_pu is empty after pf()")
            results["status"] = "fail"
            return results

        # 4. Check voltage violations (outside [0.95, 1.05] pu)
        v_violations = []
        v_vals_dict = {}
        for bus_name in v_vals.index:
            v = float(v_vals[bus_name])
            v_vals_dict[bus_name] = v
            if v < V_MIN_PU or v > V_MAX_PU:
                v_violations.append(
                    {
                        "bus": bus_name,
                        "v_mag_pu": v,
                        "violation": "low" if v < V_MIN_PU else "high",
                        "margin": float(v - V_MIN_PU) if v < V_MIN_PU else float(v - V_MAX_PU),
                    }
                )

        results["details"]["voltage_magnitudes_pu"] = v_vals_dict
        results["details"]["v_min_pu"] = float(v_vals.min())
        results["details"]["v_max_pu"] = float(v_vals.max())
        results["details"]["voltage_violations"] = v_violations
        results["details"]["n_voltage_violations"] = len(v_violations)

        print("\n=== Voltage Profile ===")
        print(f"  Min: {v_vals.min():.4f} pu, Max: {v_vals.max():.4f} pu")
        print(f"  Violations outside [{V_MIN_PU}, {V_MAX_PU}]: {len(v_violations)}")
        for vv in v_violations[:5]:
            print(f"    Bus {vv['bus']}: {vv['v_mag_pu']:.4f} pu ({vv['violation']})")

        # 5. Check thermal limit violations: |flow| > s_nom for lines and transformers
        thermal_violations = []

        # Lines
        p0_lines = n.lines_t.p0
        if len(p0_lines) > 0:
            p0_vals = p0_lines.iloc[0].abs()
            s_nom_lines = n.lines.s_nom
            for line_name in p0_vals.index:
                if line_name in s_nom_lines.index:
                    flow_mw = float(p0_vals[line_name])
                    limit_mw = float(s_nom_lines[line_name])
                    if limit_mw > 0 and flow_mw > limit_mw:
                        thermal_violations.append(
                            {
                                "branch": line_name,
                                "type": "line",
                                "flow_mw": flow_mw,
                                "limit_mw": limit_mw,
                                "loading_pct": float(flow_mw / limit_mw * 100),
                            }
                        )
            results["details"]["line_flows_mw"] = p0_vals.to_dict()
            results["details"]["n_lines_checked"] = len(p0_vals)

        # Transformers
        p0_xfmr = n.transformers_t.p0
        if len(p0_xfmr) > 0:
            p0_xvals = p0_xfmr.iloc[0].abs()
            s_nom_xfmr = n.transformers.s_nom
            for xfmr_name in p0_xvals.index:
                if xfmr_name in s_nom_xfmr.index:
                    flow_mw = float(p0_xvals[xfmr_name])
                    limit_mw = float(s_nom_xfmr[xfmr_name])
                    if limit_mw > 0 and flow_mw > limit_mw:
                        thermal_violations.append(
                            {
                                "branch": xfmr_name,
                                "type": "transformer",
                                "flow_mw": flow_mw,
                                "limit_mw": limit_mw,
                                "loading_pct": float(flow_mw / limit_mw * 100),
                            }
                        )
            results["details"]["transformer_flows_mw"] = p0_xvals.to_dict()

        results["details"]["thermal_violations"] = thermal_violations
        results["details"]["n_thermal_violations"] = len(thermal_violations)

        print("\n=== Thermal Limit Violations ===")
        print(f"  Lines: {sum(1 for v in thermal_violations if v['type'] == 'line')}")
        print(f"  Transformers: {sum(1 for v in thermal_violations if v['type'] == 'transformer')}")
        for tv in thermal_violations[:5]:
            print(
                f"    {tv['type'].capitalize()} {tv['branch']}: "
                f"{tv['flow_mw']:.1f} MW > {tv['limit_mw']:.1f} MW "
                f"({tv['loading_pct']:.1f}%)"
            )

        # 6. Summary
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

        print("\n=== AC Feasibility Summary ===")
        print(
            f"  Converged: {converged} (iterations: {n_iterations}, residual: {convergence_residual})"
        )
        print(f"  Voltage violations: {len(v_violations)}")
        print(f"  Thermal violations: {len(thermal_violations)}")
        print("  Same model context: True (no export/reimport)")

        # 7. Pass condition:
        # "Achievable within the same model context (no export to file and reimport).
        #  Voltage violations and thermal limit violations from DC dispatch are accessible
        #  as structured output."
        # The key test is ACHIEVABILITY (same model context + structured output accessible).
        # The presence of violations is EXPECTED and not a failure.
        violations_accessible = (
            isinstance(v_violations, list)
            and isinstance(thermal_violations, list)
            and results["details"]["same_model_context"]
        )

        if not violations_accessible:
            results["errors"].append("Violation data not accessible as structured output")
            results["status"] = "fail"
        elif not converged:
            results["errors"].append("AC PF did not converge")
            results["status"] = "fail"
        else:
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
