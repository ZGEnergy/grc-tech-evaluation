"""
Test C-10: Distributed slack DC OPF on MEDIUM.

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus)
Pass condition: Distributed slack DC OPF on MEDIUM.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS

CASCADED FAILURE: A-11 FAILED -- distributed_slack is hardcoded to False in the
linear OPF formulation (linear_opf_ts.py line 3022). The PowerFlowOptions.distributed_slack
flag is ignored by the OPF. No API exists for setting distributed slack weights in OPF.

This test does NOT attempt execution. It records the cascaded failure from A-11.
"""

from __future__ import annotations

import json
import os
import time


def run(
    network_file: str = "data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Record C-10 as cascaded failure from A-11."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()

    # Record CPU thread info even for cascaded failure
    cpu_threads_available = os.cpu_count() or 1
    results["details"]["cpu_threads_used"] = 0  # Not executed
    results["details"]["cpu_threads_available"] = cpu_threads_available

    results["details"]["blocked_by"] = "A-11"
    results["details"]["cascaded_failure"] = True
    results["details"]["reason"] = (
        "A-11 (distributed slack DC OPF on TINY) FAILED because GridCal's linear OPF "
        "formulation hardcodes distributed_slack=False in its internal LinearAnalysis "
        "call. The PowerFlowOptions.distributed_slack flag is ignored by the OPF. "
        "No API exists for setting distributed slack weights in the OPF context. "
        "Since the feature does not work on TINY, it cannot be scaled to MEDIUM."
    )
    results["details"]["a11_failure_summary"] = {
        "a11_status": "fail",
        "a11_workaround_class": "blocking",
        "root_cause": "OPF hardcodes distributed_slack=False in PTDF computation",
        "source_location": "linear_opf_ts.py line 3022",
        "pf_distributed_slack_works": True,
        "opf_distributed_slack_works": False,
    }
    results["errors"].append(
        "Cascaded failure from A-11: distributed slack is not functional in "
        "GridCal's DC OPF formulation. Cannot scale to MEDIUM."
    )

    results["wall_clock_seconds"] = time.perf_counter() - start
    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
