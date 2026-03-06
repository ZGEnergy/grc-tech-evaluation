"""A-1 (dcpf) — DC Power Flow on IEEE 39-bus (TINY).

Pass condition: Converges. Nodal injections, line flows, and voltage angles
accessible as structured output (DataFrame, dict, or named array — not raw solver vector).
"""

from __future__ import annotations

import time
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case39.m")


def load_network(filepath: str | Path) -> pypsa.Network:
    """Load MATPOWER .m into PyPSA via matpowercaseframes."""
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
    return n


def run() -> dict:
    """Execute A-1 DC power flow test."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network(CASE_FILE)
        details["buses"] = len(n.buses)
        details["lines"] = len(n.lines)
        details["transformers"] = len(n.transformers)
        details["generators"] = len(n.generators)

        # Run DC power flow (linear PF)
        t0 = time.perf_counter()
        n.lpf()
        wall_clock = time.perf_counter() - t0

        # Check convergence — lpf always converges (linear solve)
        details["wall_clock_seconds"] = round(wall_clock, 6)

        # Extract structured outputs
        v_ang = n.buses_t.v_ang
        details["v_ang_shape"] = list(v_ang.shape)
        details["v_ang_type"] = type(v_ang).__name__
        details["v_ang_sample"] = v_ang.iloc[0, :5].to_dict()

        line_flows = n.lines_t.p0
        details["line_flows_shape"] = list(line_flows.shape)
        details["line_flows_type"] = type(line_flows).__name__
        details["line_flows_sample"] = line_flows.iloc[0, :5].to_dict()

        # Nodal injections (p from buses_t)
        p_bus = n.buses_t.p
        details["bus_p_shape"] = list(p_bus.shape)
        details["bus_p_type"] = type(p_bus).__name__

        # Verify non-trivial results
        assert v_ang.abs().sum().sum() > 0, "All voltage angles are zero"
        assert line_flows.abs().sum().sum() > 0, "All line flows are zero"

        # Check power balance (total gen ~ total load)
        total_gen = n.generators_t.p.sum(axis=1).iloc[0]
        total_load = n.loads.p_set.sum()
        details["total_generation_mw"] = round(float(total_gen), 2)
        details["total_load_mw"] = round(float(total_load), 2)
        details["power_balance_mw"] = round(float(total_gen - total_load), 2)

        # Output format assessment
        details["output_format"] = "pandas DataFrame (time-indexed rows, component-indexed columns)"

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(str(e))
        wall_clock = 0.0

    return {
        "test_id": "A-1",
        "slug": "dcpf",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": round(wall_clock, 6),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
