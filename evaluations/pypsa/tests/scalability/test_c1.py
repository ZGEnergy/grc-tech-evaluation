"""
Test C-1: DCPF at scale (MEDIUM — 10k-bus network)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses)
Pass condition: Converges. Record wall_clock and peak_memory.
Tool: pypsa 1.1.2
"""

from __future__ import annotations

import json
import resource
import time
import traceback
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"


def _load_network(case_file: str) -> pypsa.Network:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    cf = CaseFrames(str(DATA_DIR / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return net


def run() -> dict:
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "peak_memory_mb": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    _mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # kB on Linux
    try:
        # 1. Load MEDIUM network
        net = _load_network("case_ACTIVSg10k.m")
        load_time = time.perf_counter() - start

        results["details"]["bus_count"] = len(net.buses)
        results["details"]["line_count"] = len(net.lines)
        results["details"]["transformer_count"] = len(net.transformers)
        results["details"]["generator_count"] = len(net.generators)
        results["details"]["load_time_seconds"] = load_time

        # 2. Solve DCPF (linear power flow)
        solve_start = time.perf_counter()
        net.lpf()
        solve_time = time.perf_counter() - solve_start

        results["details"]["solve_time_seconds"] = solve_time

        # 3. Validate results
        bus_angles = net.buses_t.v_ang
        line_p0 = net.lines_t.p0

        assert bus_angles.shape[0] > 0, "No snapshot results"
        assert bus_angles.shape[1] == len(net.buses), "Angle count mismatch"

        angles = bus_angles.iloc[0]
        non_zero = angles[angles.abs() > 1e-12]
        assert len(non_zero) > 0, "All voltage angles are zero"

        max_flow = line_p0.iloc[0].abs().max()
        assert max_flow > 0, "All line flows are zero"

        results["details"]["angle_range_rad"] = [float(angles.min()), float(angles.max())]
        results["details"]["max_line_flow_mw"] = float(max_flow)
        results["details"]["total_generation_mw"] = float(net.generators_t.p.iloc[0].sum())

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        results["peak_memory_mb"] = mem_after / 1024.0  # Convert kB to MB

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
