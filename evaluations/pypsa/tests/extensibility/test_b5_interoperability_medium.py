"""B-5 (interoperability) -- Export DCPF results to DataFrame + CSV on ACTIVSg10k (MEDIUM)."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

CASE_FILE = Path("/workspace/data/networks/case_ACTIVSg10k.m")


def load_network(filepath):
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


def run():
    errors = []
    workarounds = []
    details = {}
    try:
        n = load_network(CASE_FILE)
        n.lpf()
        t0 = time.perf_counter()
        v_ang = n.buses_t.v_ang
        line_flows = n.lines_t.p0
        gen_dispatch = n.generators_t.p
        bus_p = n.buses_t.p
        details["v_ang_type"] = type(v_ang).__name__
        details["v_ang_shape"] = list(v_ang.shape)
        details["line_flows_shape"] = list(line_flows.shape)
        details["gen_dispatch_shape"] = list(gen_dispatch.shape)
        with tempfile.TemporaryDirectory() as tmpdir:
            v_ang.to_csv(f"{tmpdir}/voltage_angles.csv")
            line_flows.to_csv(f"{tmpdir}/line_flows.csv")
            gen_dispatch.to_csv(f"{tmpdir}/gen_dispatch.csv")
            bus_p.to_csv(f"{tmpdir}/bus_injections.csv")
            v_ang_read = pd.read_csv(f"{tmpdir}/voltage_angles.csv", index_col=0)
            details["csv_roundtrip_shape"] = list(v_ang_read.shape)
            details["csv_roundtrip_match"] = bool(v_ang_read.shape == v_ang.shape)
            details["csv_files"] = {}
            for fname in [
                "voltage_angles.csv",
                "line_flows.csv",
                "gen_dispatch.csv",
                "bus_injections.csv",
            ]:
                details["csv_files"][fname] = os.path.getsize(f"{tmpdir}/{fname}")
        wall_clock = time.perf_counter() - t0
        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["api_method"] = "Results are native pandas DataFrames. Export: df.to_csv()."
        details["loc_export"] = 4
        details["loc_total"] = 4
        status = "PASS"
    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
    return {
        "test_id": "B-5",
        "slug": "interoperability",
        "tier": "MEDIUM",
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
