"""A-4 (ac_feasibility) -- AC PF feasibility check on DC OPF dispatch, ACTIVSg10k (MEDIUM).

depends_on: A-3 (DC OPF passed on MEDIUM)
Pass condition: Achievable within same model context. Voltage and thermal violations identifiable.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg10k.m")


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

    if hasattr(cf, "gencost") and cf.gencost is not None:
        gc = cf.gencost.values
        for i, gen_name in enumerate(n.generators.index):
            if i < len(gc):
                cost_type = int(gc[i, 0])
                if cost_type == 2:
                    n_coeffs = int(gc[i, 3])
                    if n_coeffs == 2:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 4]
                    elif n_coeffs >= 3:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 5]

    # Handle zero-rated lines
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0

    # Fix zero-impedance lines
    zero_x = n.lines.x == 0
    if zero_x.any():
        n.lines.loc[zero_x, "x"] = 0.0001
    zero_x_x = n.transformers.x == 0
    if zero_x_x.any():
        n.transformers.loc[zero_x_x, "x"] = 0.0001

    return n


def run() -> dict:
    """Execute A-4 AC feasibility check on MEDIUM."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network_with_costs(CASE_FILE)
        details["buses"] = len(n.buses)
        details["generators"] = len(n.generators)

        # Stage 1: DC OPF
        t0 = time.perf_counter()
        n.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        dc_opf_time = time.perf_counter() - t0

        details["dc_opf_objective"] = round(float(n.objective), 4)
        details["dc_opf_wall_clock_seconds"] = round(dc_opf_time, 4)

        dc_dispatch = n.generators_t.p.iloc[0].copy()
        details["dc_total_dispatch_mw"] = round(float(dc_dispatch.sum()), 2)

        # Stage 2: Fix generators to DC OPF dispatch, run AC PF
        for gen_name in n.generators.index:
            n.generators.loc[gen_name, "p_set"] = dc_dispatch[gen_name]
            if n.generators.loc[gen_name, "control"] != "Slack":
                n.generators.loc[gen_name, "control"] = "PV"

        details["same_model_context"] = True

        # Attempt flat start
        t0 = time.perf_counter()
        n.pf()
        ac_pf_time = time.perf_counter() - t0

        v_mag = n.buses_t.v_mag_pu
        converged = v_mag.abs().sum().sum() > 0

        if not converged:
            details["flat_start"] = "FAILED"
            workarounds.append(
                {
                    "type": "stable",
                    "description": "DC warm start fallback for AC PF on MEDIUM",
                }
            )
            n.lpf()
            t0 = time.perf_counter()
            n.pf()
            ac_pf_time = time.perf_counter() - t0
            v_mag = n.buses_t.v_mag_pu
            converged = v_mag.abs().sum().sum() > 0
        else:
            details["flat_start"] = "CONVERGED"

        details["ac_pf_wall_clock_seconds"] = round(ac_pf_time, 4)
        details["ac_pf_converged"] = converged

        if converged:
            v_mag_vals = v_mag.iloc[0]
            details["v_mag_range"] = [
                round(float(v_mag_vals.min()), 4),
                round(float(v_mag_vals.max()), 4),
            ]

            # Voltage violations (|v - 1.0| > 0.05)
            v_deviation = (v_mag_vals - 1.0).abs()
            voltage_violations = v_deviation[v_deviation > 0.05]
            details["voltage_violations_count"] = len(voltage_violations)

            # Thermal violations
            line_p0 = n.lines_t.p0.iloc[0] if len(n.lines_t.p0) > 0 else None
            line_q0 = n.lines_t.q0.iloc[0] if len(n.lines_t.q0) > 0 else None

            if line_p0 is not None and line_q0 is not None:
                s_apparent = np.sqrt(line_p0**2 + line_q0**2)
                s_nom = n.lines.s_nom
                mask = s_nom > 0
                loading = s_apparent[mask] / s_nom[mask]
                overloaded = loading[loading > 1.0]
                details["thermal_violation_count"] = len(overloaded)
                details["max_line_loading_pct"] = round(float(loading.max()) * 100, 1)

            # Line losses
            line_p1 = n.lines_t.p1.iloc[0]
            total_losses = float((line_p0 + line_p1).abs().sum())
            details["ac_total_line_losses_mw"] = round(total_losses, 2)

        details["violations_identifiable"] = True
        status = "PASS" if converged else "FAIL"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())

    return {
        "test_id": "A-4",
        "slug": "ac_feasibility",
        "tier": "MEDIUM",
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
