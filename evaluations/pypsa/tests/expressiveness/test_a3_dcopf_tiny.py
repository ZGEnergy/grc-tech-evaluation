"""A-3 (dcopf) — DC OPF with gen costs and line flow limits on IEEE 39-bus (TINY).

Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable
from solution.

IMPORTANT: PyPSA's pypower importer does NOT import gencost. We must manually
set marginal_cost from the gencost data. case39.m has quadratic costs:
type=2, n=3, coefficients [c2=0.01, c1=0.3, c0=0.2] for all 10 generators.
"""

from __future__ import annotations

import time
from pathlib import Path

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
    # case39 gencost: type=2 (polynomial), n=3, [c2, c1, c0] = [0.01, 0.3, 0.2]
    gencost = cf.gencost
    for i, gen_name in enumerate(n.generators.index):
        row = gencost.iloc[i]
        n_cost = int(row["NCOST"])
        if n_cost == 3:
            # Quadratic: cost = c2*P^2 + c1*P + c0
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]  # linear term
            n.generators.loc[gen_name, "marginal_cost_quadratic"] = row["C2"]  # quadratic term
        elif n_cost == 2:
            # Linear: cost = c1*P + c0
            n.generators.loc[gen_name, "marginal_cost"] = row["C1"]

    return n


def run() -> dict:
    """Execute A-3 DC OPF test."""
    errors = []
    workarounds = []
    details = {}

    workarounds.append(
        {
            "type": "stable",
            "description": (
                "Must manually set marginal_cost and marginal_cost_quadratic on generators "
                "after import, since import_from_pypower_ppc ignores gencost data."
            ),
        }
    )

    try:
        n = load_network_with_costs(CASE_FILE)
        details["generators_with_costs"] = n.generators[
            ["bus", "p_nom", "marginal_cost", "marginal_cost_quadratic"]
        ].to_dict(orient="index")

        # Run DC OPF with HiGHS
        t0 = time.perf_counter()
        status_result = n.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["solver_status"] = str(status_result)
        details["objective_value"] = round(float(n.objective), 4)

        # Extract dispatch
        gen_dispatch = n.generators_t.p
        details["dispatch_shape"] = list(gen_dispatch.shape)
        details["dispatch"] = {k: round(v, 2) for k, v in gen_dispatch.iloc[0].to_dict().items()}
        details["total_dispatch_mw"] = round(float(gen_dispatch.sum(axis=1).iloc[0]), 2)
        details["total_load_mw"] = round(float(n.loads.p_set.sum()), 2)

        # Extract LMPs (marginal prices at buses)
        lmps = n.buses_t.marginal_price
        details["lmp_shape"] = list(lmps.shape)
        details["lmp_sample"] = {k: round(v, 4) for k, v in lmps.iloc[0, :10].to_dict().items()}
        details["lmp_range"] = [
            round(float(lmps.values.min()), 4),
            round(float(lmps.values.max()), 4),
        ]
        details["lmp_mean"] = round(float(lmps.values.mean()), 4)

        # Line flows
        line_flows = n.lines_t.p0
        details["line_flows_sample"] = {
            k: round(v, 2) for k, v in line_flows.iloc[0, :5].to_dict().items()
        }

        # Check for binding line constraints
        line_loading = (line_flows.iloc[0].abs() / n.lines.s_nom).round(4)
        binding = line_loading[line_loading >= 0.999]
        details["binding_lines"] = len(binding)
        details["binding_line_names"] = list(binding.index)

        details["output_format"] = "pandas DataFrame"

        assert gen_dispatch.abs().sum().sum() > 0, "No generation dispatched"
        assert lmps.abs().sum().sum() > 0, "All LMPs are zero"

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        wall_clock = 0.0

    return {
        "test_id": "A-3",
        "slug": "dcopf",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", round(wall_clock, 6)),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
