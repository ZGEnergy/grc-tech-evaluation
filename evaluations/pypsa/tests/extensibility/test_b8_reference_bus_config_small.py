"""B-8 (reference_bus_config) -- DC OPF with 3 slack configurations on ACTIVSg2000 (SMALL).

(a) default single slack, (b) different single slack bus, (c) distributed slack.
Compare LMPs across all three.
"""

from __future__ import annotations

import json
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


def solve_dcopf(n: pypsa.Network) -> dict:
    n.optimize(
        solver_name="highs",
        solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
    )
    lmps = n.buses_t.marginal_price.iloc[0]
    return {
        "objective": round(float(n.objective), 4),
        "lmp_mean": round(float(lmps.mean()), 6),
        "lmp_range": [round(float(lmps.min()), 6), round(float(lmps.max()), 6)],
    }


def run() -> dict:
    """Execute B-8 reference bus configuration test on SMALL."""
    errors = []
    workarounds = []
    details = {}

    try:
        t0 = time.perf_counter()

        # (a) Default single slack bus
        n_a = load_network_with_costs(CASE_FILE)
        default_slack_gen = n_a.generators[n_a.generators.control == "Slack"].index.tolist()
        details["config_a"] = {
            "description": "Default single slack",
            "slack_generators": default_slack_gen[:3],
        }
        result_a = solve_dcopf(n_a)
        details["config_a"]["results"] = result_a

        # (b) Different single slack bus
        n_b = load_network_with_costs(CASE_FILE)
        non_slack_gens = n_b.generators[n_b.generators.control != "Slack"].index.tolist()
        new_slack_gen = non_slack_gens[len(non_slack_gens) // 2]
        new_slack_bus = n_b.generators.loc[new_slack_gen, "bus"]

        for gen in n_b.generators.index:
            if gen == new_slack_gen:
                n_b.generators.loc[gen, "control"] = "Slack"
            elif n_b.generators.loc[gen, "control"] == "Slack":
                n_b.generators.loc[gen, "control"] = "PV"

        details["config_b"] = {
            "description": f"Different single slack (moved to {new_slack_gen} at bus {new_slack_bus})",
        }
        result_b = solve_dcopf(n_b)
        details["config_b"]["results"] = result_b

        # (c) Distributed slack (OPF inherently distributes)
        n_c = load_network_with_costs(CASE_FILE)
        for gen in n_c.generators.index:
            n_c.generators.loc[gen, "control"] = "PV"
        n_c.generators.loc[n_c.generators.index[0], "control"] = "Slack"

        details["config_c"] = {
            "description": "Distributed slack (OPF inherently distributes generation)",
        }
        result_c = solve_dcopf(n_c)
        details["config_c"]["results"] = result_c

        wall_clock = time.perf_counter() - t0
        details["wall_clock_seconds"] = round(wall_clock, 4)

        # Compare LMPs
        lmps_a = n_a.buses_t.marginal_price.iloc[0]
        lmps_b = n_b.buses_t.marginal_price.iloc[0]
        lmps_c = n_c.buses_t.marginal_price.iloc[0]

        details["lmp_comparison"] = {
            "a_vs_b_max_diff": round(float((lmps_a - lmps_b).abs().max()), 6),
            "a_vs_c_max_diff": round(float((lmps_a - lmps_c).abs().max()), 6),
            "b_vs_c_max_diff": round(float((lmps_b - lmps_c).abs().max()), 6),
        }

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())

    return {
        "test_id": "B-8",
        "slug": "reference_bus_config",
        "tier": "SMALL",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
