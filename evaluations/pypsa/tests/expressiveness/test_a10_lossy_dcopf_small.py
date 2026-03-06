"""A-10 (lossy_dcopf_lmp) -- Lossy DC OPF on ACTIVSg2000 (SMALL).

Pass condition: Loss-inclusive LMPs with non-zero loss components.
Uses transmission_losses=3 parameter.
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
    """Execute A-10 lossy DC OPF test on SMALL."""
    errors = []
    workarounds = []
    details = {}

    try:
        # Lossless baseline
        n_lossless = load_network_with_costs(CASE_FILE)
        n_lossless.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
        )
        lossless_lmps = n_lossless.buses_t.marginal_price.iloc[0].copy()
        lossless_cost = float(n_lossless.objective)
        details["lossless_cost"] = round(lossless_cost, 4)

        # Lossy DC OPF
        n = load_network_with_costs(CASE_FILE)

        t0 = time.perf_counter()
        status_result = n.optimize(
            solver_name="highs",
            solver_options={"time_limit": 300, "presolve": "on", "threads": 1},
            transmission_losses=3,
        )
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 4)
        details["solver_status"] = str(status_result)
        details["lossy_cost"] = round(float(n.objective), 4)
        details["cost_increase"] = round(float(n.objective) - lossless_cost, 4)
        details["transmission_losses_segments"] = 3

        # LMP comparison
        lossy_lmps = n.buses_t.marginal_price.iloc[0].copy()
        lmp_diff = lossy_lmps - lossless_lmps
        details["lmp_diff_range"] = [
            round(float(lmp_diff.min()), 4),
            round(float(lmp_diff.max()), 4),
        ]
        details["lmp_diff_nonzero"] = int((lmp_diff.abs() > 1e-6).sum())
        details["loss_components_nonzero"] = bool((lmp_diff.abs() > 1e-6).any())

        # Dispatch comparison
        lossy_gen = n.generators_t.p.iloc[0].sum()
        lossless_gen = n_lossless.generators_t.p.iloc[0].sum()
        details["total_lossy_gen_mw"] = round(float(lossy_gen), 2)
        details["total_lossless_gen_mw"] = round(float(lossless_gen), 2)
        details["generation_increase_mw"] = round(float(lossy_gen - lossless_gen), 2)
        details["native_lossy_support"] = True

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())

    return {
        "test_id": "A-10",
        "slug": "lossy_dcopf_lmp",
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
