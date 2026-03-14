"""
Test B-2: BFS to depth 3 from a chosen bus

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Works via native graph primitives or clean, documented export
    to NetworkX (Python) or Graphs.jl (Julia).
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

BFS_ROOT_BUS = 0  # pandapower 0-indexed (MATPOWER bus 1)
BFS_DEPTH = 3


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute BFS graph access test and return structured results."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import networkx as nx
        import pandapower.topology as top

        # 1. Load network
        net = load_pandapower(network_file)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)

        # 2. Create NetworkX graph via documented pandapower API
        graph_start = time.perf_counter()
        mg = top.create_nxgraph(net, respect_switches=True)
        graph_time = time.perf_counter() - graph_start
        results["details"]["graph_creation_seconds"] = graph_time

        results["details"]["graph_type"] = type(mg).__name__
        results["details"]["graph_node_count"] = mg.number_of_nodes()
        results["details"]["graph_edge_count"] = mg.number_of_edges()
        results["details"]["graph_nodes"] = sorted(list(mg.nodes()))

        # Verify the root bus exists in the graph
        if BFS_ROOT_BUS not in mg:
            results["errors"].append(
                f"Root bus {BFS_ROOT_BUS} not in graph. Available: {sorted(mg.nodes())}"
            )
            return results

        # 3. BFS to depth 3 using NetworkX
        bfs_start = time.perf_counter()
        bfs_tree = nx.bfs_tree(mg, source=BFS_ROOT_BUS, depth_limit=BFS_DEPTH)
        bfs_time = time.perf_counter() - bfs_start
        results["details"]["bfs_seconds"] = bfs_time

        bfs_nodes = sorted(list(bfs_tree.nodes()))
        bfs_edges = list(bfs_tree.edges())
        results["details"]["bfs_root_bus"] = BFS_ROOT_BUS
        results["details"]["bfs_depth_limit"] = BFS_DEPTH
        results["details"]["bfs_node_count"] = len(bfs_nodes)
        results["details"]["bfs_edge_count"] = len(bfs_edges)
        results["details"]["bfs_nodes"] = bfs_nodes
        results["details"]["bfs_edges"] = bfs_edges

        # 4. Compute depth of each discovered node
        depths = nx.single_source_shortest_path_length(mg, BFS_ROOT_BUS, cutoff=BFS_DEPTH)
        depth_distribution = {}
        for node, depth in depths.items():
            depth_distribution.setdefault(depth, []).append(node)
        results["details"]["depth_distribution"] = {
            k: sorted(v) for k, v in sorted(depth_distribution.items())
        }
        results["details"]["max_depth_reached"] = max(depths.values()) if depths else 0

        # 5. Verify BFS correctness
        # All discovered nodes should be within depth 3
        if max(depths.values()) > BFS_DEPTH:
            results["errors"].append(f"BFS returned nodes beyond depth {BFS_DEPTH}")

        # BFS should discover at least the root + some neighbors
        if len(bfs_nodes) < 2:
            results["errors"].append(
                f"BFS discovered only {len(bfs_nodes)} node(s), expected at least 2"
            )

        # 6. Also test pandapower's built-in graph analysis functions
        # connected_component gives all buses reachable from a bus
        connected = set(top.connected_component(mg, BFS_ROOT_BUS))
        results["details"]["connected_component_size"] = len(connected)

        # calc_distance_to_bus gives shortest distances
        distances = top.calc_distance_to_bus(net, BFS_ROOT_BUS, respect_switches=True)
        results["details"]["distance_to_bus_sample"] = {
            int(k): float(v) for k, v in list(distances.items())[:10]
        }

        # 7. Test with impedance-weighted graph
        mg_weighted = top.create_nxgraph(
            net,
            respect_switches=True,
            calc_branch_impedances=True,
            branch_impedance_unit="ohm",
        )
        # Check that edge weights exist
        sample_edge = list(mg_weighted.edges(data=True))[0]
        edge_attrs = list(sample_edge[2].keys()) if len(sample_edge) > 2 else []
        results["details"]["weighted_graph_edge_attrs"] = edge_attrs
        has_impedance = any(attr in edge_attrs for attr in ["z_ohm", "r_ohm", "x_ohm", "weight"])
        results["details"]["impedance_weighted"] = has_impedance

        # BFS on weighted graph (same result since BFS is unweighted)
        bfs_weighted = nx.bfs_tree(mg_weighted, source=BFS_ROOT_BUS, depth_limit=BFS_DEPTH)
        results["details"]["bfs_weighted_node_count"] = bfs_weighted.number_of_nodes()

        # 8. Check pass conditions
        # - Graph created via documented API (create_nxgraph)
        # - BFS works via standard NetworkX (bfs_tree)
        # - Nodes discovered at correct depths
        if len(bfs_nodes) >= 2 and max(depths.values()) <= BFS_DEPTH:
            results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
