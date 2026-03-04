"""
Test C-5: N-M contingency sweep at scale (MEDIUM — 10k-bus network)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses)
Pass condition: Completes. Record total_time, per_case_average, cases_per_order.
Tool: pypsa 1.1.2
Parameters: x=5 (graph distance), m=4 (max outage order)
"""

from __future__ import annotations

import json
import resource
import time
import traceback
from itertools import combinations
from pathlib import Path

import networkx as nx
import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"

GRAPH_DISTANCE = 5
MAX_OUTAGE_ORDER = 4


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


def _get_bus_load(net: pypsa.Network, bus: str) -> float:
    bus_loads = net.loads[net.loads["bus"] == bus]
    return float(bus_loads["p_set"].sum()) if len(bus_loads) > 0 else 0.0


def _get_branches_within_distance(
    net: pypsa.Network, center_bus: str, distance: int
) -> list[tuple[str, str]]:
    G = net.graph()
    buses_within = set()
    for node, depth in nx.single_source_shortest_path_length(G, center_bus).items():
        if depth <= distance:
            buses_within.add(node)

    branches = []
    for line_name in net.lines.index:
        bus0 = net.lines.at[line_name, "bus0"]
        bus1 = net.lines.at[line_name, "bus1"]
        if bus0 in buses_within and bus1 in buses_within:
            branches.append(("Line", line_name))

    for trafo_name in net.transformers.index:
        bus0 = net.transformers.at[trafo_name, "bus0"]
        bus1 = net.transformers.at[trafo_name, "bus1"]
        if bus0 in buses_within and bus1 in buses_within:
            branches.append(("Transformer", trafo_name))

    return branches


def _solve_dcpf_with_outages(
    net: pypsa.Network,
    outaged_branches: list[tuple[str, str]],
) -> dict:
    # Disable branches
    for comp_type, comp_name in outaged_branches:
        if comp_type == "Line":
            net.lines.at[comp_name, "active"] = False
        elif comp_type == "Transformer":
            net.transformers.at[comp_name, "active"] = False

    result = {"converged": False, "total_load_loss": 0.0}
    try:
        net.lpf()
        result["converged"] = True

        G = net.graph(include_inactive=False)
        components = list(nx.connected_components(G))
        if len(components) > 1:
            slack_buses = net.buses[net.buses["control"] == "Slack"].index
            slack_bus = slack_buses[0] if len(slack_buses) > 0 else net.buses.index[0]
            main_comp = None
            for comp in components:
                if slack_bus in comp:
                    main_comp = comp
                    break
            for comp in components:
                if comp == main_comp:
                    continue
                for bus in comp:
                    result["total_load_loss"] += _get_bus_load(net, bus)
    except Exception:
        pass
    finally:
        for comp_type, comp_name in outaged_branches:
            if comp_type == "Line":
                net.lines.at[comp_name, "active"] = True
            elif comp_type == "Transformer":
                net.transformers.at[comp_name, "active"] = True

    return result


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
        results["details"]["bus_count"] = len(net.buses)
        results["details"]["line_count"] = len(net.lines)
        results["details"]["graph_distance"] = GRAPH_DISTANCE
        results["details"]["max_outage_order"] = MAX_OUTAGE_ORDER

        # Choose a central bus (pick highest-degree bus for interesting contingencies)
        G = net.graph()
        degrees = dict(G.degree())
        center_bus = max(degrees, key=degrees.get)
        results["details"]["center_bus"] = center_bus
        results["details"]["center_bus_degree"] = degrees[center_bus]

        # 2. Enumerate branches within distance
        branches = _get_branches_within_distance(net, center_bus, GRAPH_DISTANCE)
        results["details"]["branches_in_scope"] = len(branches)

        # 3. Base case DCPF
        net.lpf()

        # 4. Sweep N-1 through N-m
        contingency_summary = {}
        pruned_branches = set()
        total_cases = 0
        order_times = {}

        for order in range(1, MAX_OUTAGE_ORDER + 1):
            surviving = [b for b in branches if b not in pruned_branches]
            if len(surviving) < order:
                contingency_summary[f"N-{order}"] = {
                    "surviving_branches": len(surviving),
                    "cases_evaluated": 0,
                    "skipped": "insufficient surviving branches",
                }
                continue

            cases = list(combinations(surviving, order))
            n_cases = len(cases)

            order_start = time.perf_counter()
            cases_with_loss = 0
            max_loss = 0.0

            for combo in cases:
                cr = _solve_dcpf_with_outages(net, list(combo))
                if cr["total_load_loss"] > 0:
                    cases_with_loss += 1
                    max_loss = max(max_loss, cr["total_load_loss"])
                    # Prune branches that cause load loss
                    for b in combo:
                        pruned_branches.add(b)

            order_time = time.perf_counter() - order_start
            order_times[f"N-{order}"] = order_time
            total_cases += n_cases

            contingency_summary[f"N-{order}"] = {
                "surviving_branches": len(surviving),
                "cases_evaluated": n_cases,
                "cases_with_load_loss": cases_with_loss,
                "max_load_loss_mw": max_loss,
                "pruned_after": len(pruned_branches),
                "time_seconds": order_time,
            }

        results["details"]["contingency_summary"] = contingency_summary
        results["details"]["total_cases_evaluated"] = total_cases
        results["details"]["order_times"] = order_times
        results["details"]["per_case_average_seconds"] = (
            (time.perf_counter() - start) / total_cases if total_cases > 0 else 0.0
        )
        results["details"]["cases_per_order"] = {
            k: v.get("cases_evaluated", 0) for k, v in contingency_summary.items()
        }
        results["details"]["total_pruned"] = len(pruned_branches)

        results["status"] = "pass"

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
