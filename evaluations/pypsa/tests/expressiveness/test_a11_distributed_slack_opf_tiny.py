"""A-11 (distributed_slack_opf) — Distributed Slack OPF on IEEE 39-bus (TINY).

Pass condition: Tool supports distributed slack formulation. LMPs differ from
single-slack A-3. Distributed slack weights are settable via API.

PyPSA supports distribute_slack in n.pf() but NOT in n.optimize(). The optimize()
formulation uses implicit power balance (no explicit slack bus), so LMPs are
already independent of slack bus choice. However, true distributed slack
(where losses are allocated proportionally) is a different concept.
"""

from __future__ import annotations

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
    """Execute A-11 distributed slack OPF test."""
    errors = []
    workarounds = []
    details = {}

    try:
        # ---- Part 1: Check if optimize() has distribute_slack parameter ----
        import inspect

        sig = inspect.signature(pypsa.Network().optimize.__call__)
        params = list(sig.parameters.keys())
        has_distribute_slack_in_optimize = "distribute_slack" in params
        details["optimize_has_distribute_slack_param"] = has_distribute_slack_in_optimize

        # ---- Part 2: Standard single-slack DC OPF (A-3 baseline) ----
        n_single = load_network_with_costs(CASE_FILE)
        n_single.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        single_lmps = n_single.buses_t.marginal_price.iloc[0].copy()
        single_cost = float(n_single.objective)
        details["single_slack_cost"] = round(single_cost, 4)
        details["single_slack_lmp_sample"] = {
            k: round(v, 4) for k, v in single_lmps.iloc[:10].to_dict().items()
        }

        # ---- Part 3: Change slack bus and re-solve ----
        # In lossless DC OPF, changing the slack bus should NOT change dispatch or
        # LMPs because the formulation uses power balance constraints, not an
        # explicit slack variable. This is unlike power flow where slack matters.
        n2 = load_network_with_costs(CASE_FILE)
        pv_gens = n2.generators[n2.generators.control == "PV"]
        old_slack_gen = n2.generators[n2.generators.control == "Slack"].index[0]
        new_slack_gen = pv_gens.index[0]
        n2.generators.loc[old_slack_gen, "control"] = "PV"
        n2.generators.loc[new_slack_gen, "control"] = "Slack"
        details["original_slack_bus"] = str(n_single.generators.loc[old_slack_gen, "bus"])
        details["new_slack_bus"] = str(n2.generators.loc[new_slack_gen, "bus"])

        n2.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        alt_lmps = n2.buses_t.marginal_price.iloc[0].copy()
        alt_cost = float(n2.objective)
        details["alt_slack_cost"] = round(alt_cost, 4)

        lmp_diff_slack = alt_lmps - single_lmps
        details["lmp_diff_by_slack_change_max"] = round(float(lmp_diff_slack.abs().max()), 6)
        details["cost_diff_by_slack_change"] = round(alt_cost - single_cost, 6)
        details["lmps_change_with_slack_bus"] = bool(lmp_diff_slack.abs().max() > 1e-4)

        # ---- Part 4: Test distribute_slack in PF (not OPF) ----
        n3 = load_network_with_costs(CASE_FILE)
        try:
            n3.pf(distribute_slack=True)
            details["pf_distribute_slack_works"] = True
            details["pf_distribute_slack_method"] = "n.pf(distribute_slack=True)"
        except Exception as e:
            details["pf_distribute_slack_works"] = False
            details["pf_distribute_slack_error"] = str(e)

        n4 = load_network_with_costs(CASE_FILE)
        n4.pf(distribute_slack=False)
        details["pf_single_slack_works"] = True

        # Compare PF results with and without distributed slack
        if details.get("pf_distribute_slack_works"):
            pf_dist_gen = n3.generators_t.p.iloc[0]
            pf_single_gen = n4.generators_t.p.iloc[0]
            gen_diff = pf_dist_gen - pf_single_gen
            details["pf_gen_diff_by_slack_method"] = {
                k: round(v, 4) for k, v in gen_diff.to_dict().items()
            }
            details["pf_dispatch_differs"] = bool(gen_diff.abs().max() > 1e-4)

        # ---- Part 5: Summary ----
        details["assessment"] = (
            "PyPSA's n.optimize() (DC OPF) does not have a distribute_slack parameter. "
            "The optimization formulation uses implicit power balance constraints, making "
            "LMPs independent of slack bus choice in the lossless DC case. "
            "n.pf(distribute_slack=True) is available for power flow but not optimization. "
            "For lossy DC OPF (A-10), LMPs naturally vary by bus due to loss allocation, "
            "which achieves a similar effect to distributed slack."
        )

        # This is a genuine limitation — distributed slack OPF is not supported
        workarounds.append(
            {
                "type": "stable",
                "description": (
                    "n.optimize() has no distribute_slack. In lossless DC OPF, LMPs are "
                    "already slack-independent. For loss-inclusive distributed reference, "
                    "use transmission_losses parameter (A-10) which naturally distributes "
                    "loss components across buses."
                ),
            }
        )

        # FAIL: the tool does not support distributed slack in the optimization
        status = "FAIL"
        errors.append(
            "PyPSA does not support distributed slack in n.optimize(). "
            "The parameter exists only in n.pf() for power flow."
        )

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")

    return {
        "test_id": "A-11",
        "slug": "distributed_slack_opf",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": 0,
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
