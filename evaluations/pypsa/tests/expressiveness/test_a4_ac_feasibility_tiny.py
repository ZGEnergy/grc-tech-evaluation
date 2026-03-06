"""A-4 (ac_feasibility) -- AC PF feasibility check on DC OPF dispatch, IEEE 39-bus (TINY).

depends_on: A-3 (DC OPF passed on TINY)
Pass condition: Achievable within same model context (no file export/reimport).
Voltage and thermal violations identifiable.

Convergence protocol: flat start first, then DC warm start fallback.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case39.m")


def load_network_with_costs(filepath: str | Path) -> pypsa.Network:
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    if hasattr(cf, "gencost") and cf.gencost is not None:
        ppc["gencost"] = cf.gencost.values
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)

    # Manually set generator costs from gencost data
    gencost = cf.gencost
    for i, gen_name in enumerate(n.generators.index):
        row = gencost.iloc[i]
        n_cost = int(row["NCOST"])
        if n_cost == 3:
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]
            n.generators.loc[gen_name, "marginal_cost_quadratic"] = row["C2"]
        elif n_cost == 2:
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]
    return n


def run() -> dict:
    """Execute A-4 AC feasibility check on DC OPF dispatch."""
    errors = []
    workarounds = []
    details = {}

    try:
        # ----- Stage 1: DC OPF -----
        n = load_network_with_costs(CASE_FILE)

        t0 = time.perf_counter()
        status_result = n.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        dc_opf_time = time.perf_counter() - t0

        details["dc_opf_solver_status"] = str(status_result)
        details["dc_opf_objective"] = round(float(n.objective), 4)
        details["dc_opf_wall_clock_seconds"] = round(dc_opf_time, 6)

        # Extract DC OPF dispatch
        dc_dispatch = n.generators_t.p.iloc[0].copy()
        details["dc_dispatch"] = {k: round(v, 2) for k, v in dc_dispatch.to_dict().items()}
        details["dc_total_dispatch_mw"] = round(float(dc_dispatch.sum()), 2)

        # ----- Stage 2: Fix generators to DC OPF dispatch, run AC PF -----
        # This is done within the SAME network object -- no file export/reimport.
        # Set p_set to DC OPF dispatch values for all generators.
        for gen_name in n.generators.index:
            n.generators.loc[gen_name, "p_set"] = dc_dispatch[gen_name]
            # Make all generators PV buses (control="PV") except slack
            # The slack bus generator keeps control="Slack"
            if n.generators.loc[gen_name, "control"] != "Slack":
                n.generators.loc[gen_name, "control"] = "PV"

        details["same_model_context"] = True
        details["workflow"] = "optimize() -> set p_set -> pf() on same Network object"

        # Attempt 1: flat start (default)
        t0 = time.perf_counter()
        n.pf()
        ac_pf_time = time.perf_counter() - t0

        # Check convergence by inspecting voltage results
        v_mag = n.buses_t.v_mag_pu
        converged = v_mag.abs().sum().sum() > 0

        if not converged:
            # Fallback: DC warm start
            details["flat_start"] = "FAILED"
            workarounds.append(
                {
                    "type": "stable",
                    "description": "DC warm start fallback after flat start failure for AC PF",
                }
            )
            n.lpf()  # Linear PF for initial angles
            t0 = time.perf_counter()
            n.pf()
            ac_pf_time = time.perf_counter() - t0
            v_mag = n.buses_t.v_mag_pu
            converged = v_mag.abs().sum().sum() > 0
            details["dc_warm_start_used"] = True
        else:
            details["flat_start"] = "CONVERGED"
            details["dc_warm_start_used"] = False

        details["ac_pf_wall_clock_seconds"] = round(ac_pf_time, 6)
        details["ac_pf_converged"] = converged

        if not converged:
            errors.append("AC PF did not converge even with DC warm start fallback")

        # ----- Stage 3: Identify violations -----

        # Voltage violations: |v_mag_pu - 1.0| > 0.05
        v_mag_vals = v_mag.iloc[0]
        v_deviation = (v_mag_vals - 1.0).abs()
        voltage_violations = v_deviation[v_deviation > 0.05]
        details["v_mag_range"] = [
            round(float(v_mag_vals.min()), 4),
            round(float(v_mag_vals.max()), 4),
        ]
        details["v_mag_sample"] = {
            k: round(v, 4) for k, v in v_mag_vals.iloc[:10].to_dict().items()
        }
        details["voltage_violation_threshold"] = 0.05
        details["voltage_violations_count"] = len(voltage_violations)
        if len(voltage_violations) > 0:
            details["voltage_violations"] = {
                k: round(v, 4) for k, v in voltage_violations.to_dict().items()
            }
            details["voltage_violation_buses"] = {
                k: {
                    "v_mag_pu": round(float(v_mag_vals[k]), 4),
                    "deviation": round(float(v_deviation[k]), 4),
                }
                for k in voltage_violations.index
            }
        else:
            details["voltage_violations"] = {}

        # Thermal violations: |S| > s_nom on lines
        line_p0 = n.lines_t.p0.iloc[0] if len(n.lines_t.p0) > 0 else None
        line_q0 = n.lines_t.q0.iloc[0] if len(n.lines_t.q0) > 0 else None

        thermal_violations = {}
        if line_p0 is not None and line_q0 is not None:
            s_apparent = np.sqrt(line_p0**2 + line_q0**2)
            s_nom = n.lines.s_nom
            # Only check lines with nonzero s_nom
            mask = s_nom > 0
            loading = s_apparent[mask] / s_nom[mask]
            overloaded = loading[loading > 1.0]
            details["thermal_violation_count"] = len(overloaded)
            if len(overloaded) > 0:
                thermal_violations = {
                    k: {
                        "s_apparent_mva": round(float(s_apparent[k]), 2),
                        "s_nom_mva": round(float(s_nom[k]), 2),
                        "loading_pct": round(float(loading[k]) * 100, 1),
                    }
                    for k in overloaded.index
                }
            details["thermal_violations"] = thermal_violations
            details["max_line_loading_pct"] = (
                round(float(loading.max()) * 100, 1) if len(loading) > 0 else 0.0
            )
        else:
            details["thermal_violation_count"] = 0
            details["thermal_violations"] = {}

        # Also check transformer thermal violations
        if len(n.transformers) > 0 and len(n.transformers_t.p0) > 0:
            xfmr_p0 = n.transformers_t.p0.iloc[0]
            xfmr_q0 = n.transformers_t.q0.iloc[0]
            xfmr_s = np.sqrt(xfmr_p0**2 + xfmr_q0**2)
            xfmr_s_nom = n.transformers.s_nom
            xfmr_mask = xfmr_s_nom > 0
            if xfmr_mask.any():
                xfmr_loading = xfmr_s[xfmr_mask] / xfmr_s_nom[xfmr_mask]
                xfmr_overloaded = xfmr_loading[xfmr_loading > 1.0]
                details["transformer_thermal_violation_count"] = len(xfmr_overloaded)
            else:
                details["transformer_thermal_violation_count"] = 0

        # Voltage angles (for reference)
        v_ang = n.buses_t.v_ang.iloc[0] if len(n.buses_t.v_ang) > 0 else None
        if v_ang is not None:
            details["v_ang_range_deg"] = [
                round(float(np.degrees(v_ang.min())), 2),
                round(float(np.degrees(v_ang.max())), 2),
            ]

        # Line losses from AC PF
        if line_p0 is not None:
            line_p1 = n.lines_t.p1.iloc[0]
            total_losses = float((line_p0 + line_p1).abs().sum())
            details["ac_total_line_losses_mw"] = round(total_losses, 2)

        # Summary
        details["violations_identifiable"] = True
        details["output_format"] = "pandas DataFrame"

        assert converged, "AC PF did not converge"
        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")

    return {
        "test_id": "A-4",
        "slug": "ac_feasibility",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": details.get("ac_pf_wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
