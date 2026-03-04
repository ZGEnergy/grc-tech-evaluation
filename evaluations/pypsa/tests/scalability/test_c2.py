"""
Test C-2: ACPF at scale (MEDIUM — 10k-bus network)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses)
Pass condition: Converges (or documents convergence failure). Record wall_clock,
    peak_memory, iterations.
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
    try:
        # 1. Load MEDIUM network
        net = _load_network("case_ACTIVSg10k.m")
        load_time = time.perf_counter() - start

        results["details"]["bus_count"] = len(net.buses)
        results["details"]["line_count"] = len(net.lines)
        results["details"]["transformer_count"] = len(net.transformers)
        results["details"]["generator_count"] = len(net.generators)
        results["details"]["load_time_seconds"] = load_time

        # 2. Solve ACPF (full Newton-Raphson power flow)
        solve_start = time.perf_counter()
        info = net.pf()
        solve_time = time.perf_counter() - solve_start

        results["details"]["solve_time_seconds"] = solve_time

        # 3. Extract convergence info
        # net.pf() returns Dict with keys: 'n_iter', 'error', 'converged'
        # Each is a DataFrame indexed by snapshot, columns = sub-network indices
        converged_df = info.get("converged")
        n_iter_df = info.get("n_iter")
        error_df = info.get("error")

        converged_all = bool(converged_df.all().all()) if converged_df is not None else False

        iteration_info = {}
        if converged_df is not None and n_iter_df is not None:
            for sub_net in converged_df.columns:
                conv = bool(converged_df.iloc[0][sub_net])
                n_iter = int(n_iter_df.iloc[0][sub_net])
                err = float(error_df.iloc[0][sub_net]) if error_df is not None else None
                iteration_info[f"sub_network_{sub_net}"] = {
                    "converged": conv,
                    "n_iter": n_iter,
                    "error": err,
                }

        results["details"]["convergence"] = iteration_info
        results["details"]["converged_all"] = converged_all

        # 4. Extract results
        bus_v_mag = net.buses_t.v_mag_pu
        bus_v_ang = net.buses_t.v_ang
        line_p0 = net.lines_t.p0

        if len(bus_v_mag) > 0:
            v_mag = bus_v_mag.iloc[0]
            results["details"]["v_mag_range"] = [float(v_mag.min()), float(v_mag.max())]
            results["details"]["v_mag_mean"] = float(v_mag.mean())

        if len(bus_v_ang) > 0:
            v_ang = bus_v_ang.iloc[0]
            results["details"]["v_ang_range_rad"] = [float(v_ang.min()), float(v_ang.max())]

        if len(line_p0) > 0:
            flows = line_p0.iloc[0].dropna()
            results["details"]["max_line_flow_mw"] = (
                float(flows.abs().max()) if len(flows) > 0 else 0.0
            )

        # Total iterations
        total_iters = sum(v["n_iter"] for v in iteration_info.values() if v["n_iter"] > 0)
        results["details"]["total_iterations"] = total_iters

        if converged_all:
            results["status"] = "pass"
        else:
            results["status"] = "qualified_pass"
            results["errors"].append(
                "ACPF did not converge for all sub-networks — see convergence details"
            )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        results["peak_memory_mb"] = mem_after / 1024.0

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
