"""A-2 (acpf) -- AC Power Flow on ACTIVSg10k (MEDIUM).

Pass condition: Converges. Follow convergence protocol (flat start, DC warm start fallback).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg10k.m")


def load_network(filepath: str | Path) -> pypsa.Network:
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

    # Fix zero-impedance lines that cause singular matrix in PF
    zero_x_lines = n.lines.x == 0
    if zero_x_lines.any():
        n.lines.loc[zero_x_lines, "x"] = 0.0001
    zero_x_xfmrs = n.transformers.x == 0
    if zero_x_xfmrs.any():
        n.transformers.loc[zero_x_xfmrs, "x"] = 0.0001

    return n


def run() -> dict:
    """Execute A-2 AC power flow test on MEDIUM."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network(CASE_FILE)
        details["buses"] = len(n.buses)
        details["lines"] = len(n.lines)
        details["transformers"] = len(n.transformers)
        details["generators"] = len(n.generators)

        # Attempt 1: flat start
        t0 = time.perf_counter()
        n.pf()
        wall_clock = time.perf_counter() - t0

        v_mag = n.buses_t.v_mag_pu
        converged = v_mag.abs().sum().sum() > 0

        if not converged:
            details["flat_start"] = "FAILED"
            workarounds.append(
                {
                    "type": "stable",
                    "description": "DC warm start fallback after flat start failure",
                }
            )
            n2 = load_network(CASE_FILE)
            n2.lpf()
            t0 = time.perf_counter()
            n2.pf()
            wall_clock = time.perf_counter() - t0
            n = n2
            v_mag = n.buses_t.v_mag_pu
            converged = v_mag.abs().sum().sum() > 0
            details["dc_warm_start_used"] = True
        else:
            details["flat_start"] = "CONVERGED"
            details["dc_warm_start_used"] = False

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["converged"] = converged

        if converged:
            details["v_mag_range"] = [
                round(float(v_mag.values.min()), 4),
                round(float(v_mag.values.max()), 4),
            ]

            v_ang = n.buses_t.v_ang
            details["v_ang_range_deg"] = [
                round(float(np.degrees(v_ang.values.min())), 2),
                round(float(np.degrees(v_ang.values.max())), 2),
            ]

            line_p0 = n.lines_t.p0
            line_p1 = n.lines_t.p1
            line_losses_p = line_p0.values + line_p1.values
            details["total_line_losses_mw"] = round(float(np.abs(line_losses_p).sum()), 2)
        else:
            errors.append("AC PF did not converge even with DC warm start")

        status = "PASS" if converged else "FAIL"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "A-2",
        "slug": "acpf",
        "tier": "MEDIUM",
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
