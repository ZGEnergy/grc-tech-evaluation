"""A-3 (dcopf) -- DC OPF on ACTIVSg10k (MEDIUM).

Pass condition: Converges. Record time, objective.
IMPORTANT: 2459/9726 lines have s_nom=0. Must handle before OPF.
"""

from __future__ import annotations

import time
from pathlib import Path

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
    zero_lines = (n.lines.s_nom == 0).sum()
    zero_xfmrs = (n.transformers.s_nom == 0).sum()
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0

    # Fix zero-impedance lines
    zero_x = n.lines.x == 0
    if zero_x.any():
        n.lines.loc[zero_x, "x"] = 0.0001
    zero_x_x = n.transformers.x == 0
    if zero_x_x.any():
        n.transformers.loc[zero_x_x, "x"] = 0.0001

    return n, zero_lines, zero_xfmrs


def run() -> dict:
    """Execute A-3 DC OPF test on MEDIUM."""
    errors = []
    workarounds = []
    details = {}

    try:
        n, zero_lines, zero_xfmrs = load_network_with_costs(CASE_FILE)
        details["buses"] = len(n.buses)
        details["generators"] = len(n.generators)
        details["lines"] = len(n.lines)
        details["transformers"] = len(n.transformers)
        details["zero_rated_lines_fixed"] = int(zero_lines)
        details["zero_rated_transformers_fixed"] = int(zero_xfmrs)

        t0 = time.perf_counter()
        status_result = n.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["solver_status"] = str(status_result)
        details["objective_value"] = round(float(n.objective), 4)

        gen_dispatch = n.generators_t.p
        details["total_dispatch_mw"] = round(float(gen_dispatch.sum(axis=1).iloc[0]), 2)
        details["total_load_mw"] = round(float(n.loads.p_set.sum()), 2)

        lmps = n.buses_t.marginal_price
        details["lmp_range"] = [
            round(float(lmps.values.min()), 4),
            round(float(lmps.values.max()), 4),
        ]
        details["lmp_mean"] = round(float(lmps.values.mean()), 4)

        line_loading = (n.lines_t.p0.iloc[0].abs() / n.lines.s_nom).fillna(0)
        binding = line_loading[line_loading >= 0.999]
        details["binding_lines"] = len(binding)

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "A-3",
        "slug": "dcopf",
        "tier": "MEDIUM",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", round(wall_clock, 4)),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
