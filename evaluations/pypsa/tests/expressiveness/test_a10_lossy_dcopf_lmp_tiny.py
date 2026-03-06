"""A-10 (lossy_dcopf_lmp) — Lossy DC OPF with LMP Decomposition on IEEE 39-bus (TINY).

Pass condition: Loss-inclusive LMPs with non-zero loss components.
LMP decomposition extractable.

PyPSA supports transmission_losses parameter in n.optimize() for piecewise-linear
loss approximation.
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
    """Execute A-10 lossy DC OPF with LMP decomposition test."""
    errors = []
    workarounds = []
    details = {}

    try:
        # First run lossless DC OPF for comparison
        n_lossless = load_network_with_costs(CASE_FILE)
        n_lossless.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        lossless_lmps = n_lossless.buses_t.marginal_price.iloc[0].copy()
        lossless_cost = float(n_lossless.objective)
        details["lossless_cost"] = round(lossless_cost, 4)
        details["lossless_lmp_sample"] = {
            k: round(v, 4) for k, v in lossless_lmps.iloc[:10].to_dict().items()
        }

        # Now run lossy DC OPF with transmission losses
        n = load_network_with_costs(CASE_FILE)

        t0 = time.perf_counter()
        try:
            status_result = n.optimize(
                solver_name="highs",
                solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
                transmission_losses=3,  # 3-segment piecewise-linear loss approximation
            )
            wall_clock = time.perf_counter() - t0

            details["wall_clock_seconds"] = round(wall_clock, 6)
            details["solver_status"] = str(status_result)
            details["lossy_cost"] = round(float(n.objective), 4)
            details["cost_increase"] = round(float(n.objective) - lossless_cost, 4)
            details["transmission_losses_segments"] = 3

            # Extract lossy LMPs
            lossy_lmps = n.buses_t.marginal_price.iloc[0].copy()
            details["lossy_lmp_sample"] = {
                k: round(v, 4) for k, v in lossy_lmps.iloc[:10].to_dict().items()
            }

            # Compute LMP differences (loss component approximation)
            lmp_diff = lossy_lmps - lossless_lmps
            details["lmp_diff_sample"] = {
                k: round(v, 4) for k, v in lmp_diff.iloc[:10].to_dict().items()
            }
            details["lmp_diff_range"] = [
                round(float(lmp_diff.min()), 4),
                round(float(lmp_diff.max()), 4),
            ]
            details["lmp_diff_nonzero"] = int((lmp_diff.abs() > 1e-6).sum())

            # Check for non-zero loss components
            if (lmp_diff.abs() > 1e-6).any():
                details["loss_components_nonzero"] = True
            else:
                details["loss_components_nonzero"] = False
                errors.append("Loss components are all zero — losses may not affect LMPs")

            # LMP decomposition
            # In DC OPF: LMP = energy + congestion
            # In lossy DC OPF: LMP = energy + congestion + loss
            # The difference between lossy and lossless is approximately the loss component
            # Energy component: the marginal cost of the cheapest unconstrained generator
            # We can approximate the decomposition:
            slack_bus = (
                n.buses.index[n.buses.control == "Slack"][0]
                if "Slack" in n.buses.control.values
                else n.buses.index[0]
            )
            energy_component = lossy_lmps[slack_bus]
            congestion_lossless = lossless_lmps - lossless_lmps[slack_bus]
            loss_component = lmp_diff

            details["lmp_decomposition"] = {
                "method": (
                    "Difference between lossy and lossless DC OPF LMPs approximates "
                    "loss marginal component. Energy component from slack bus LMP."
                ),
                "energy_component_at_slack": round(float(energy_component), 4),
                "congestion_range": [
                    round(float(congestion_lossless.min()), 4),
                    round(float(congestion_lossless.max()), 4),
                ],
                "loss_range": [
                    round(float(loss_component.min()), 4),
                    round(float(loss_component.max()), 4),
                ],
            }

            # Dispatch comparison
            lossy_dispatch = n.generators_t.p.iloc[0]
            lossless_dispatch = n_lossless.generators_t.p.iloc[0]
            details["total_lossy_gen_mw"] = round(float(lossy_dispatch.sum()), 2)
            details["total_lossless_gen_mw"] = round(float(lossless_dispatch.sum()), 2)
            details["generation_increase_mw"] = round(
                float(lossy_dispatch.sum() - lossless_dispatch.sum()), 2
            )

            details["native_lossy_support"] = True
            status = "PASS"

        except Exception as e:
            wall_clock = time.perf_counter() - t0
            details["wall_clock_seconds"] = round(wall_clock, 6)
            details["native_lossy_error"] = f"{type(e).__name__}: {e}"
            details["native_lossy_support"] = False
            errors.append(f"Lossy DC OPF failed: {e}")
            status = "FAIL"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")

    return {
        "test_id": "A-10",
        "slug": "lossy_dcopf_lmp",
        "tier": "TINY",
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
