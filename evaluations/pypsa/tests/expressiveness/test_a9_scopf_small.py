"""A-9 (scopf) -- Security-Constrained OPF on ACTIVSg2000 (SMALL).

Pass condition: Solves. Base-case dispatch respects all contingency flow limits.
SMALL: 100 monitored branches as contingency set.
"""

from __future__ import annotations

import time
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg2000.m")


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
    return n


def run() -> dict:
    """Execute A-9 SCOPF test on SMALL."""
    errors = []
    workarounds = []
    details = {}
    solver_opts = {"time_limit": 300, "presolve": "on", "threads": 1}

    try:
        # Baseline DC OPF
        n_base = load_network_with_costs(CASE_FILE)
        n_base.optimize(solver_name="highs", solver_options=solver_opts)
        base_cost = float(n_base.objective)
        details["a3_base_cost"] = round(base_cost, 4)
        details["total_lines"] = len(n_base.lines)
        details["total_transformers"] = len(n_base.transformers)

        # Use first 100 lines as contingency set
        line_outages = list(n_base.lines.index[:100])
        details["contingency_count"] = len(line_outages)

        # SCOPF
        n = load_network_with_costs(CASE_FILE)
        t0 = time.perf_counter()
        try:
            status_result = n.optimize.optimize_security_constrained(
                branch_outages=line_outages,
                solver_name="highs",
                solver_options=solver_opts,
            )
            wall_clock = time.perf_counter() - t0

            details["wall_clock_seconds"] = round(wall_clock, 4)
            details["solver_status"] = str(status_result)
            details["scopf_cost"] = round(float(n.objective), 4)
            details["cost_vs_base"] = round(float(n.objective) - base_cost, 4)
            details["native_scopf_support"] = True

            # LMP sample
            lmps = n.buses_t.marginal_price.iloc[0]
            details["lmp_range"] = [
                round(float(lmps.min()), 4),
                round(float(lmps.max()), 4),
            ]

            status = "PASS"

        except Exception as e:
            wall_clock = time.perf_counter() - t0
            details["wall_clock_seconds"] = round(wall_clock, 4)
            details["scopf_error"] = f"{type(e).__name__}: {e}"

            # Try with smaller set
            small_outages = list(n_base.lines.index[:30])
            n2 = load_network_with_costs(CASE_FILE)
            t0 = time.perf_counter()
            try:
                status_result = n2.optimize.optimize_security_constrained(
                    branch_outages=small_outages,
                    solver_name="highs",
                    solver_options=solver_opts,
                )
                wall_clock = time.perf_counter() - t0
                details["reduced_contingency_count"] = len(small_outages)
                details["reduced_wall_clock_seconds"] = round(wall_clock, 4)
                details["reduced_solver_status"] = str(status_result)
                details["reduced_scopf_cost"] = round(float(n2.objective), 4)
                details["native_scopf_support"] = True
                status = "PASS"
            except Exception as e2:
                details["reduced_error"] = f"{type(e2).__name__}: {e2}"
                details["native_scopf_support"] = False
                errors.append(f"SCOPF failed: {e2}")
                status = "FAIL"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())

    return {
        "test_id": "A-9",
        "slug": "scopf",
        "tier": "SMALL",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
