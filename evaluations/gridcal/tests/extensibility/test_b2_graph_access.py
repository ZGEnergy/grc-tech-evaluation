"""
Test B-2: From a chosen bus, run BFS to depth 3 and return subgraph.

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Works via native graph primitives or clean, documented export to NetworkX.
Tool: gridcal (VeraGridEngine) 5.6.28
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute B-2 graph access test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import networkx as nx

        # 1. Load network
        grid = load_gridcal(network_file)
        n_buses = grid.get_bus_number()
        n_branches = grid.get_branch_number()
        results["details"]["bus_count"] = n_buses
        results["details"]["branch_count"] = n_branches

        # 2. Export to NetworkX graph via documented API
        graph = grid.build_graph()
        results["details"]["graph_type"] = type(graph).__name__
        results["details"]["graph_nodes"] = graph.number_of_nodes()
        results["details"]["graph_edges"] = graph.number_of_edges()

        # Verify it is a proper NetworkX graph
        assert isinstance(graph, nx.MultiDiGraph), (
            f"Expected MultiDiGraph, got {type(graph).__name__}"
        )

        # 3. Choose a starting bus (bus index 0 = first bus)
        # Graph nodes are Bus objects, not strings or integers
        graph_nodes = list(graph.nodes())
        start_bus = graph_nodes[0]
        start_name = start_bus.name if hasattr(start_bus, "name") else str(start_bus)
        results["details"]["start_bus"] = start_name
        results["details"]["node_type"] = type(start_bus).__name__

        # 4. Run BFS to depth 3 using NetworkX
        # Use single_source_shortest_path_length to find all nodes within depth 3
        bfs_nodes = set()
        for node, depth in nx.single_source_shortest_path_length(
            graph, start_bus, cutoff=3
        ).items():
            bfs_nodes.add(node)

        results["details"]["bfs_depth"] = 3
        results["details"]["bfs_node_count"] = len(bfs_nodes)
        results["details"]["bfs_node_names"] = [
            n.name if hasattr(n, "name") else str(n) for n in bfs_nodes
        ]

        # 5. Extract subgraph
        subgraph = graph.subgraph(bfs_nodes).copy()
        results["details"]["subgraph_nodes"] = subgraph.number_of_nodes()
        results["details"]["subgraph_edges"] = subgraph.number_of_edges()

        # 6. Verify subgraph properties
        # BFS from bus 1 should reach several neighboring buses
        has_nodes = subgraph.number_of_nodes() > 1
        has_edges = subgraph.number_of_edges() > 0
        is_connected = nx.is_weakly_connected(subgraph)

        results["details"]["subgraph_is_connected"] = is_connected
        results["details"]["has_multiple_nodes"] = has_nodes
        results["details"]["has_edges"] = has_edges

        # Verify depth layering
        depth_layers = {}
        for node, depth in nx.single_source_shortest_path_length(
            graph, start_bus, cutoff=3
        ).items():
            node_name = node.name if hasattr(node, "name") else str(node)
            depth_layers.setdefault(depth, []).append(node_name)

        results["details"]["depth_layers"] = {str(k): v for k, v in sorted(depth_layers.items())}

        # 7. Check pass condition
        pass_checks = {
            "graph_is_networkx": isinstance(graph, nx.MultiDiGraph),
            "bfs_found_nodes": len(bfs_nodes) > 1,
            "subgraph_has_edges": has_edges,
            "subgraph_connected": is_connected,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
