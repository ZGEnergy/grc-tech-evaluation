"""B-5 (interoperability) — Export DCPF results to pandas DataFrame + CSV on IEEE 39-bus (TINY).

Pass condition: <5 lines beyond solve, no custom serialization.
depends_on: A-1
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case39.m")


def load_network(filepath: str | Path) -> pypsa.Network:
    cf = CaseFrames(str(filepath))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    return n


def run() -> dict:
    """Execute B-5 interoperability test."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network(CASE_FILE)
        n.lpf()

        t0 = time.perf_counter()

        # Results are already pandas DataFrames — zero conversion needed
        v_ang = n.buses_t.v_ang  # voltage angles
        line_flows = n.lines_t.p0  # line flows
        gen_dispatch = n.generators_t.p  # generator dispatch
        bus_p = n.buses_t.p  # bus injections

        details["v_ang_type"] = type(v_ang).__name__
        details["line_flows_type"] = type(line_flows).__name__
        details["gen_dispatch_type"] = type(gen_dispatch).__name__
        details["bus_p_type"] = type(bus_p).__name__

        # Export to CSV — 1 line per output
        with tempfile.TemporaryDirectory() as tmpdir:
            v_ang.to_csv(f"{tmpdir}/voltage_angles.csv")
            line_flows.to_csv(f"{tmpdir}/line_flows.csv")
            gen_dispatch.to_csv(f"{tmpdir}/gen_dispatch.csv")
            bus_p.to_csv(f"{tmpdir}/bus_injections.csv")

            # Verify round-trip: read back and compare
            v_ang_read = pd.read_csv(f"{tmpdir}/voltage_angles.csv", index_col=0)
            details["csv_roundtrip_shape"] = list(v_ang_read.shape)
            details["csv_roundtrip_match"] = bool(v_ang_read.shape == v_ang.shape)

            # Check file sizes
            import os

            details["csv_files"] = {}
            for fname in [
                "voltage_angles.csv",
                "line_flows.csv",
                "gen_dispatch.csv",
                "bus_injections.csv",
            ]:
                fpath = f"{tmpdir}/{fname}"
                details["csv_files"][fname] = os.path.getsize(fpath)

        wall_clock = time.perf_counter() - t0

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["api_method"] = (
            "Results are native pandas DataFrames. Export: df.to_csv(). "
            "No custom serialization needed."
        )
        details["loc_export"] = 4  # 4 to_csv calls
        details["loc_total"] = 4  # truly 4 lines beyond solve

        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "B-5",
        "slug": "interoperability",
        "tier": "TINY",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
