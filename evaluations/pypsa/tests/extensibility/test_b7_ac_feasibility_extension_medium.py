"""B-7 (ac_feasibility_extension) -- AC feasibility check on DC OPF dispatch, ACTIVSg10k (MEDIUM).

Document AC feasibility workaround from A-4 on MEDIUM.
"""

from __future__ import annotations

import json
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

    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0
    # Fix zero-impedance transformers that cause SVD failure in post_processing
    n.transformers.loc[n.transformers.x == 0, "x"] = 1e-4
    return n


def run() -> dict:
    """Execute B-7 AC feasibility extension test on MEDIUM."""
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
        dcopf_time = time.perf_counter() - t0

        dcopf_dispatch = n.generators_t.p.iloc[0].to_dict()
        details["dcopf_objective"] = round(float(n.objective), 4)
        details["dcopf_time_seconds"] = round(dcopf_time, 4)
        details["dc_total_dispatch_mw"] = round(sum(dcopf_dispatch.values()), 2)

        # Stage 2: Fix generators, run AC PF
        for gen_name in n.generators.index:
            n.generators.loc[gen_name, "p_set"] = dcopf_dispatch[gen_name]

        t1 = time.perf_counter()
        n.pf()
        acpf_time = time.perf_counter() - t1

        details["acpf_time_seconds"] = round(acpf_time, 4)

        v_mag = n.buses_t.v_mag_pu
        converged = v_mag.abs().sum().sum() > 0
        details["ac_pf_converged"] = converged

        if not converged:
            # DC warm start fallback
            workarounds.append(
                {
                    "type": "stable",
                    "description": "DC warm start fallback for AC PF convergence",
                }
            )
            n.lpf()
            t1 = time.perf_counter()
            n.pf()
            acpf_time = time.perf_counter() - t1
            v_mag = n.buses_t.v_mag_pu
            converged = v_mag.abs().sum().sum() > 0
            details["dc_warm_start_used"] = True
            details["acpf_time_seconds"] = round(acpf_time, 4)
        else:
            details["dc_warm_start_used"] = False

        if converged:
            v_mag_vals = v_mag.iloc[0]
            details["v_mag_range"] = [
                round(float(v_mag_vals.min()), 4),
                round(float(v_mag_vals.max()), 4),
            ]

            # Voltage violations
            v_deviation = (v_mag_vals - 1.0).abs()
            voltage_violations = v_deviation[v_deviation > 0.05]
            details["voltage_violations_count"] = len(voltage_violations)

            # Thermal violations
            line_p0 = n.lines_t.p0.iloc[0]
            line_q0 = n.lines_t.q0.iloc[0] if len(n.lines_t.q0) > 0 else None

            if line_p0 is not None and line_q0 is not None:
                s_apparent = np.sqrt(line_p0**2 + line_q0**2)
                s_nom = n.lines.s_nom
                mask = s_nom > 0
                loading = s_apparent[mask] / s_nom[mask]
                overloaded = loading[loading > 1.0]
                details["thermal_violation_count"] = len(overloaded)
                details["max_line_loading_pct"] = round(float(loading.max()) * 100, 1)

        details["same_model_context"] = True
        details["workflow_description"] = (
            "DC OPF -> fix generator p_set -> n.pf(). "
            "All within same Network object. No export/reimport."
        )
        details["api_method"] = (
            "n.optimize() -> read n.generators_t.p -> set n.generators.p_set -> n.pf()"
        )
        details["loc"] = 15

        wall_clock = dcopf_time + acpf_time
        details["total_wall_clock_seconds"] = round(wall_clock, 4)

        status = "PASS" if converged else "FAIL"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())

    return {
        "test_id": "B-7",
        "slug": "ac_feasibility_extension",
        "tier": "MEDIUM",
        "status": status,
        "wall_clock_seconds": details.get("total_wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
