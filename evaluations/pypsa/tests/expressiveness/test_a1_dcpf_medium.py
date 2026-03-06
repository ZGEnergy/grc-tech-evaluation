"""A-1 (dcpf) -- DC Power Flow on ACTIVSg10k (MEDIUM).

Pass condition: Converges. Record wall-clock.
"""

from __future__ import annotations

import time
from pathlib import Path

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

    # Fix zero-impedance lines that cause singular B-matrix in LPF
    zero_x_lines = n.lines.x == 0
    if zero_x_lines.any():
        n.lines.loc[zero_x_lines, "x"] = 0.0001
    zero_x_xfmrs = n.transformers.x == 0
    if zero_x_xfmrs.any():
        n.transformers.loc[zero_x_xfmrs, "x"] = 0.0001

    return n


def run() -> dict:
    """Execute A-1 DC power flow test on MEDIUM."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network(CASE_FILE)
        details["buses"] = len(n.buses)
        details["lines"] = len(n.lines)
        details["transformers"] = len(n.transformers)
        details["generators"] = len(n.generators)

        t0 = time.perf_counter()
        n.lpf()
        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)

        v_ang = n.buses_t.v_ang
        details["v_ang_shape"] = list(v_ang.shape)
        details["v_ang_range"] = [
            round(float(v_ang.values.min()), 6),
            round(float(v_ang.values.max()), 6),
        ]

        line_flows = n.lines_t.p0
        details["line_flows_shape"] = list(line_flows.shape)
        details["line_flows_range_mw"] = [
            round(float(line_flows.values.min()), 2),
            round(float(line_flows.values.max()), 2),
        ]

        total_gen = n.generators_t.p.sum(axis=1).iloc[0]
        total_load = n.loads.p_set.sum()
        details["total_generation_mw"] = round(float(total_gen), 2)
        details["total_load_mw"] = round(float(total_load), 2)
        details["power_balance_mw"] = round(float(total_gen - total_load), 2)

        assert v_ang.abs().sum().sum() > 0, "All voltage angles are zero"
        assert line_flows.abs().sum().sum() > 0, "All line flows are zero"

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "A-1",
        "slug": "dcpf",
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
