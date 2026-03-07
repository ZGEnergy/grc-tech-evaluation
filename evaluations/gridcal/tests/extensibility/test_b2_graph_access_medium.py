"""B-2: Graph Access on ACTIVSg10k (MEDIUM).

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k-bus)
Pass condition: From a chosen bus, run BFS to depth 3; return all buses and
branches in subgraph. Works via native graph primitives or clean export to NetworkX.
"""

from __future__ import annotations

import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute B-2 graph access test on MEDIUM network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import networkx as nx
        import VeraGridEngine as vge

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "MEDIUM (ACTIVSg10k)"

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
        # Use undirected view for BFS since build_graph() returns MultiDiGraph
        # and some buses may only have incoming edges in the directed representation
        G_undirected = G.to_undirected()
        center_bus = 0
        center_bus_name = grid.buses[center_bus].name
        details["center_bus_index"] = center_bus
        details["center_bus_name"] = center_bus_name

        t0 = time.perf_counter()
        bfs_result = nx.single_source_shortest_path_length(G_undirected, center_bus, cutoff=3)
        t_bfs = time.perf_counter() - t0

        details["bfs_seconds"] = round(t_bfs, 6)
        subgraph_buses = set(bfs_result.keys())
        details["subgraph_bus_count"] = len(subgraph_buses)
        details["subgraph_buses_by_depth"] = {}

        for depth in range(4):
            buses_at_depth = [b for b, d in bfs_result.items() if d == depth]
            details["subgraph_buses_by_depth"][str(depth)] = {
                "count": len(buses_at_depth),
                "bus_indices": sorted(buses_at_depth)[:10],  # truncate for large networks
            }

        # ── Step 3: Find branches in subgraph ──
        # Build bus object -> index lookup for O(1) access
        t0 = time.perf_counter()
        bus_to_idx = {bus: i for i, bus in enumerate(grid.buses)}
        subgraph_branches = []
        for i, br in enumerate(branches):
            from_idx = bus_to_idx.get(br.bus_from)
            to_idx = bus_to_idx.get(br.bus_to)
            if from_idx in subgraph_buses and to_idx in subgraph_buses:
                subgraph_branches.append(
                    {
                        "index": i,
                        "name": br.name,
                        "from_bus": from_idx,
                        "to_bus": to_idx,
                        "type": type(br).__name__,
                    }
                )
        t_branch_scan = time.perf_counter() - t0

        details["subgraph_branch_count"] = len(subgraph_branches)
        details["branch_scan_seconds"] = round(t_branch_scan, 6)
        details["subgraph_branches_sample"] = subgraph_branches[:10]

        # ── Step 4: Extract NetworkX subgraph object ──
        t0 = time.perf_counter()
        H = G.subgraph(subgraph_buses).copy()
        t_sub = time.perf_counter() - t0

        details["nx_subgraph_seconds"] = round(t_sub, 6)
        details["nx_subgraph_nodes"] = H.number_of_nodes()
        details["nx_subgraph_edges"] = H.number_of_edges()

        # ── Step 5: Verify graph connectivity and structure ──
        H_undirected = H.to_undirected()
        details["subgraph_connected"] = nx.is_connected(H_undirected)
        if nx.is_connected(H_undirected):
            details["subgraph_diameter"] = nx.diameter(H_undirected)

        # ── Step 6: BFS edges ──
        bfs_edges = list(nx.bfs_edges(G_undirected, center_bus, depth_limit=3))
        details["bfs_edges_count"] = len(bfs_edges)

        # Total wall clock
        wall_clock = t_build + t_bfs + t_branch_scan + t_sub
        details["wall_clock_seconds"] = round(wall_clock, 6)

        # Assess pass condition
        if is_nx and len(subgraph_buses) > 0 and len(subgraph_branches) > 0:
            status = "pass"
            details["pass_rationale"] = (
                f"grid.build_graph() returns nx.{type(G).__name__} with "
                f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges on 10k-bus network. "
                f"BFS to depth 3 found {len(subgraph_buses)} buses, "
                f"{len(subgraph_branches)} branches. "
                f"Graph build: {round(t_build * 1000, 1)}ms, BFS: {round(t_bfs * 1000, 1)}ms."
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
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
