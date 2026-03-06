"""B-2 (graph_access) -- BFS from a bus to depth 3 on ACTIVSg10k (MEDIUM)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import networkx as nx
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
        details["buses"] = len(n.buses)
        details["lines"] = len(n.lines)
        details["transformers"] = len(n.transformers)
        t0 = time.perf_counter()
        G = n.graph()
        details["graph_type"] = type(G).__name__
        details["graph_nodes"] = G.number_of_nodes()
        details["graph_edges"] = G.number_of_edges()
        source_bus = n.buses.index[len(n.buses) // 2]
        bfs_tree = nx.bfs_tree(G, source_bus, depth_limit=3)
        depth_map = nx.single_source_shortest_path_length(G, source_bus, cutoff=3)
        buses_by_depth = {}
        for bus, depth in depth_map.items():
            buses_by_depth.setdefault(depth, []).append(bus)
        wall_clock = time.perf_counter() - t0
        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["source_bus"] = source_bus
        details["bfs_depth_limit"] = 3
        details["buses_reached"] = len(bfs_tree.nodes)
        details["edges_in_tree"] = len(bfs_tree.edges)
        details["buses_per_depth"] = {int(k): len(v) for k, v in buses_by_depth.items()}
        subgraph_buses = set(bfs_tree.nodes)
        subgraph_lines = sum(
            1
            for nm in n.lines.index
            if n.lines.loc[nm, "bus0"] in subgraph_buses
            and n.lines.loc[nm, "bus1"] in subgraph_buses
        )
        subgraph_xfmrs = sum(
            1
            for nm in n.transformers.index
            if n.transformers.loc[nm, "bus0"] in subgraph_buses
            and n.transformers.loc[nm, "bus1"] in subgraph_buses
        )
        details["subgraph_lines"] = subgraph_lines
        details["subgraph_transformers"] = subgraph_xfmrs
        details["total_subgraph_branches"] = subgraph_lines + subgraph_xfmrs
        details["api_method"] = "n.graph() -> NetworkX MultiGraph, then nx.bfs_tree()"
        details["loc"] = 5
        assert len(bfs_tree.nodes) > 1
        status = "PASS"
    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
    return {
        "test_id": "B-2",
        "slug": "graph_access",
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
