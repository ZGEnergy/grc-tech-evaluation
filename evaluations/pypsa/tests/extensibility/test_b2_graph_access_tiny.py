"""B-2 (graph_access) — BFS from a bus to depth 3 on IEEE 39-bus (TINY).

Pass condition: Works via native graph or clean NetworkX export.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import networkx as nx
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
    """Execute B-2 graph access test."""
    errors = []
    workarounds = []
    details = {}

    try:
        n = load_network(CASE_FILE)

        t0 = time.perf_counter()

        # PyPSA exposes n.graph() -> NetworkX MultiGraph
        G = n.graph()
        details["graph_type"] = type(G).__name__
        details["graph_nodes"] = G.number_of_nodes()
        details["graph_edges"] = G.number_of_edges()

        # BFS from bus "16" (arbitrary choice) to depth 3
        source_bus = "16"
        bfs_tree = nx.bfs_tree(G, source_bus, depth_limit=3)

        # Collect buses at each depth level
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
        details["buses_by_depth"] = {int(k): sorted(v) for k, v in buses_by_depth.items()}

        # Collect branches in the subgraph
        subgraph_buses = set(bfs_tree.nodes)
        subgraph_lines = [
            name
            for name in n.lines.index
            if n.lines.loc[name, "bus0"] in subgraph_buses
            and n.lines.loc[name, "bus1"] in subgraph_buses
        ]
        subgraph_transformers = [
            name
            for name in n.transformers.index
            if n.transformers.loc[name, "bus0"] in subgraph_buses
            and n.transformers.loc[name, "bus1"] in subgraph_buses
        ]
        details["subgraph_lines"] = subgraph_lines
        details["subgraph_transformers"] = subgraph_transformers
        details["total_subgraph_branches"] = len(subgraph_lines) + len(subgraph_transformers)

        details["api_method"] = "n.graph() -> NetworkX MultiGraph, then nx.bfs_tree()"
        details["loc"] = 5  # lines of code

        assert len(bfs_tree.nodes) > 1, "BFS found no neighbors"
        status = "PASS"

    except Exception as e:
        status = "FAIL"
        errors.append(f"{type(e).__name__}: {e}")
        import traceback

        errors.append(traceback.format_exc())
        wall_clock = 0.0

    return {
        "test_id": "B-2",
        "slug": "graph_access",
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
