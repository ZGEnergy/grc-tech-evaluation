"""B-7 (ac_feasibility_extension) — AC feasibility check on DC OPF dispatch (TINY).

Since A-4 hasn't been run yet, this test exercises the full workflow:
1. Run DC OPF (A-3), get dispatch
2. Fix generator P to dispatch values
3. Run AC PF, check voltage/thermal violations
Document whether this works within same model context.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case39.m")


def load_network_with_costs(filepath: str | Path) -> tuple[pypsa.Network, CaseFrames]:
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

    gc = cf.gencost
    for i, gen_name in enumerate(n.generators.index):
        row = gc.iloc[i]
        n_cost = int(row["NCOST"])
        if n_cost == 3:
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]
            n.generators.loc[gen_name, "marginal_cost_quadratic"] = row["C2"]
        elif n_cost == 2:
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]

    return n, cf


def run() -> dict:
    """Execute B-7 AC feasibility extension test."""
    errors = []
    workarounds = []
    details = {}

    try:
        n, cf = load_network_with_costs(CASE_FILE)

        # Step 1: Solve DC OPF
        t0 = time.perf_counter()
        n.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        dcopf_time = time.perf_counter() - t0

        dcopf_dispatch = n.generators_t.p.iloc[0].to_dict()
        details["dcopf_dispatch"] = {k: round(v, 2) for k, v in dcopf_dispatch.items()}
        details["dcopf_objective"] = round(float(n.objective), 4)
        details["dcopf_time_seconds"] = round(dcopf_time, 6)

        # Step 2: Fix generators to DC OPF dispatch and run AC PF
        # PyPSA approach: set p_set on generators to the DC OPF dispatch,
        # change generators from dispatchable to fixed (PQ), keep slack as slack
        t1 = time.perf_counter()

        # Set generator active power setpoints to DC OPF dispatch
        for gen_name in n.generators.index:
            n.generators.loc[gen_name, "p_set"] = dcopf_dispatch[gen_name]

        # For ACPF, generators need control type set appropriately
        # The slack generator stays as slack; PV gens stay as PV
        # PyPSA handles this via the generator's control attribute (already set from import)

        # Run full AC power flow (Newton-Raphson)
        convergence = n.pf()

        acpf_time = time.perf_counter() - t1
        details["acpf_time_seconds"] = round(acpf_time, 6)

        # Check convergence
        # n.pf() returns a dict with convergence info per sub_network
        if hasattr(convergence, "items"):
            conv_info = {str(k): v for k, v in convergence.items()}
        else:
            conv_info = str(convergence)
        details["convergence_info"] = str(conv_info)

        # Step 3: Check for voltage violations
        bus_v_mag = n.buses_t.v_mag_pu.iloc[0]
        v_min = n.buses.v_mag_pu_min if "v_mag_pu_min" in n.buses.columns else None
        v_max = n.buses.v_mag_pu_max if "v_mag_pu_max" in n.buses.columns else None

        details["v_mag_range"] = [
            round(float(bus_v_mag.min()), 6),
            round(float(bus_v_mag.max()), 6),
        ]

        voltage_violations = []
        for bus in n.buses.index:
            v = bus_v_mag[bus]
            if v_min is not None and v < n.buses.loc[bus, "v_mag_pu_min"]:
                voltage_violations.append(
                    {
                        "bus": bus,
                        "v_mag": round(v, 6),
                        "limit": round(n.buses.loc[bus, "v_mag_pu_min"], 6),
                        "type": "undervoltage",
                    }
                )
            if v_max is not None and v > n.buses.loc[bus, "v_mag_pu_max"]:
                voltage_violations.append(
                    {
                        "bus": bus,
                        "v_mag": round(v, 6),
                        "limit": round(n.buses.loc[bus, "v_mag_pu_max"], 6),
                        "type": "overvoltage",
                    }
                )

        details["voltage_violations"] = voltage_violations
        details["n_voltage_violations"] = len(voltage_violations)

        # Step 4: Check for thermal violations on lines
        line_flows_p = n.lines_t.p0.iloc[0]
        line_flows_q = (
            n.lines_t.q0.iloc[0] if hasattr(n.lines_t, "q0") and len(n.lines_t.q0) > 0 else None
        )

        thermal_violations = []
        for line_name in n.lines.index:
            s_nom = n.lines.loc[line_name, "s_nom"]
            if s_nom > 0:
                p = abs(line_flows_p[line_name])
                if line_flows_q is not None:
                    q = abs(line_flows_q[line_name])
                    apparent = np.sqrt(p**2 + q**2)
                else:
                    apparent = p
                loading = apparent / s_nom
                if loading > 1.0:
                    thermal_violations.append(
                        {
                            "line": line_name,
                            "loading": round(loading, 4),
                            "flow_mw": round(float(apparent), 2),
                            "s_nom": s_nom,
                        }
                    )

        details["thermal_violations"] = thermal_violations
        details["n_thermal_violations"] = len(thermal_violations)

        # Same-model context assessment
        details["same_model_context"] = True
        details["workflow_description"] = (
            "DC OPF -> fix generator p_set to dispatch -> run n.pf() "
            "for full Newton-Raphson ACPF. All within same Network object. "
            "No export/reimport needed."
        )

        workarounds.append(
            {
                "type": "stable",
                "description": (
                    "Must manually set p_set on generators to DC OPF dispatch values. "
                    "This is a natural pattern in PyPSA (not a workaround per se) — "
                    "the generator control types from import already distinguish "
                    "slack vs PV vs PQ."
                ),
            }
        )

        details["api_method"] = (
            "n.optimize() -> read n.generators_t.p -> set n.generators.p_set -> n.pf() -> "
            "check n.buses_t.v_mag_pu and n.lines_t.p0/q0"
        )
        details["loc"] = 15

        wall_clock = dcopf_time + acpf_time
        details["total_wall_clock_seconds"] = round(wall_clock, 6)

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "B-7",
        "slug": "ac_feasibility_extension",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": details.get("total_wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
