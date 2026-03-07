"""B-2: Graph Access on IEEE 39-bus (TINY).

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: From a chosen bus, run BFS to depth 3; return all buses and
branches in subgraph. Works via native graph primitives or clean export to NetworkX.
"""

from __future__ import annotations

import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Execute B-2 graph access test."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import networkx as nx
        import VeraGridEngine as vge

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # Load network
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        branches = list(grid.lines) + list(grid.transformers2w)
        details["total_branches"] = len(branches)

        # ── Step 1: Build graph ──
        t0 = time.perf_counter()
        G = grid.build_graph()
        t_build = time.perf_counter() - t0

        details["graph_build_seconds"] = round(t_build, 6)
        details["graph_type"] = type(G).__name__
        details["graph_nodes"] = G.number_of_nodes()
        details["graph_edges"] = G.number_of_edges()

        # Verify it is a NetworkX graph
        is_nx = isinstance(G, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph))
        details["is_networkx_graph"] = is_nx

        # Document node and edge attributes
        sample_node = list(G.nodes)[0]
        details["sample_node"] = sample_node
        details["sample_node_data"] = dict(G.nodes[sample_node])

        sample_edge = list(G.edges(data=True))[0]
        details["sample_edge"] = {
            "from": sample_edge[0],
            "to": sample_edge[1],
            "data": {k: str(v)[:100] for k, v in sample_edge[2].items()},
        }

        # ── Step 2: BFS to depth 3 from bus 0 ──
        center_bus = 0
        center_bus_name = grid.buses[center_bus].name
        details["center_bus_index"] = center_bus
        details["center_bus_name"] = center_bus_name

        t0 = time.perf_counter()
        bfs_result = nx.single_source_shortest_path_length(G, center_bus, cutoff=3)
        t_bfs = time.perf_counter() - t0

        details["bfs_seconds"] = round(t_bfs, 6)
        subgraph_buses = set(bfs_result.keys())
        details["subgraph_bus_count"] = len(subgraph_buses)
        details["subgraph_buses_by_depth"] = {}

        for depth in range(4):
            buses_at_depth = [b for b, d in bfs_result.items() if d == depth]
            details["subgraph_buses_by_depth"][str(depth)] = {
                "count": len(buses_at_depth),
                "bus_indices": sorted(buses_at_depth),
                "bus_names": [grid.buses[b].name for b in sorted(buses_at_depth)],
            }

        # ── Step 3: Find branches in subgraph ──
        subgraph_branches = []
        for i, br in enumerate(branches):
            bus_from_idx = grid.buses.index(br.bus_from)
            bus_to_idx = grid.buses.index(br.bus_to)
            if bus_from_idx in subgraph_buses and bus_to_idx in subgraph_buses:
                subgraph_branches.append(
                    {
                        "index": i,
                        "name": br.name,
                        "from_bus": bus_from_idx,
                        "to_bus": bus_to_idx,
                        "type": type(br).__name__,
                    }
                )

        details["subgraph_branch_count"] = len(subgraph_branches)
        details["subgraph_branches"] = subgraph_branches

        # ── Step 4: Extract NetworkX subgraph object ──
        t0 = time.perf_counter()
        H = G.subgraph(subgraph_buses).copy()
        t_sub = time.perf_counter() - t0

        details["nx_subgraph_seconds"] = round(t_sub, 6)
        details["nx_subgraph_nodes"] = H.number_of_nodes()
        details["nx_subgraph_edges"] = H.number_of_edges()

        # ── Step 5: Verify graph connectivity and structure ──
        # Convert to undirected for connectivity check
        H_undirected = H.to_undirected()
        details["subgraph_connected"] = nx.is_connected(H_undirected)
        details["subgraph_diameter"] = (
            nx.diameter(H_undirected) if nx.is_connected(H_undirected) else None
        )

        # ── Step 6: Alternative graph traversal — BFS via NetworkX ──
        bfs_edges = list(nx.bfs_edges(G, center_bus, depth_limit=3))
        details["bfs_edges_count"] = len(bfs_edges)
        details["bfs_edges_sample"] = bfs_edges[:5]

        # Total wall clock
        wall_clock = details["graph_build_seconds"] + details["bfs_seconds"]

        # Assess pass condition
        if is_nx and len(subgraph_buses) > 0 and len(subgraph_branches) > 0:
            status = "pass"
            details["pass_rationale"] = (
                "grid.build_graph() returns nx.MultiDiGraph. BFS via "
                "nx.single_source_shortest_path_length works natively. "
                "All buses and branches in subgraph extracted cleanly."
            )
        else:
            status = "fail"
            errors.append("Graph access or BFS failed")

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": wall_clock,
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
