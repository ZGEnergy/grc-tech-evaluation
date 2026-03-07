"""
Test B-2: From a chosen bus, run BFS to depth 3. Return all buses and branches
    within that subgraph.

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Works via native graph primitives or clean, documented export to NetworkX.
Tool: pandapower v3.4.0

APPROACH: Use pandapower.topology.create_nxgraph() to get a NetworkX MultiGraph,
then use NetworkX BFS with depth limit. This is a documented, public API.
"""

import json
import time
import traceback

from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.topology import create_nxgraph


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute BFS graph access test and return structured results."""
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
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)

        # 2. Create NetworkX graph via pandapower's documented API
        graph = create_nxgraph(net, respect_switches=True)
        results["details"]["graph_type"] = type(graph).__name__
        results["details"]["graph_nodes"] = graph.number_of_nodes()
        results["details"]["graph_edges"] = graph.number_of_edges()

        # 3. Choose a starting bus (bus 0 -- typically a well-connected bus)
        start_bus = 0
        bfs_depth = 3
        results["details"]["start_bus"] = start_bus
        results["details"]["bfs_depth"] = bfs_depth

        # 4. Run BFS to depth 3 using NetworkX
        # bfs_edges gives all edges in BFS order
        list(nx.bfs_edges(graph, start_bus, depth_limit=bfs_depth))

        # Collect all buses within depth 3
        # Use single_source_shortest_path_length for exact depth tracking
        distances = dict(nx.single_source_shortest_path_length(graph, start_bus, cutoff=bfs_depth))
        buses_in_subgraph = sorted(distances.keys())
        results["details"]["buses_in_subgraph"] = buses_in_subgraph
        results["details"]["bus_count_in_subgraph"] = len(buses_in_subgraph)

        # Record depth of each bus
        bus_depths = {int(bus): int(depth) for bus, depth in distances.items()}
        results["details"]["bus_depths"] = bus_depths

        # 5. Identify branches (lines + trafos) within the subgraph
        bus_set = set(buses_in_subgraph)

        lines_in_subgraph = []
        for idx in net.line.index:
            from_bus = int(net.line.at[idx, "from_bus"])
            to_bus = int(net.line.at[idx, "to_bus"])
            if from_bus in bus_set and to_bus in bus_set:
                lines_in_subgraph.append(
                    {
                        "type": "line",
                        "index": int(idx),
                        "from_bus": from_bus,
                        "to_bus": to_bus,
                    }
                )

        trafos_in_subgraph = []
        for idx in net.trafo.index:
            hv_bus = int(net.trafo.at[idx, "hv_bus"])
            lv_bus = int(net.trafo.at[idx, "lv_bus"])
            if hv_bus in bus_set and lv_bus in bus_set:
                trafos_in_subgraph.append(
                    {
                        "type": "trafo",
                        "index": int(idx),
                        "hv_bus": hv_bus,
                        "lv_bus": lv_bus,
                    }
                )

        results["details"]["lines_in_subgraph"] = lines_in_subgraph
        results["details"]["trafos_in_subgraph"] = trafos_in_subgraph
        results["details"]["line_count_in_subgraph"] = len(lines_in_subgraph)
        results["details"]["trafo_count_in_subgraph"] = len(trafos_in_subgraph)
        results["details"]["total_branches_in_subgraph"] = len(lines_in_subgraph) + len(
            trafos_in_subgraph
        )

        # 6. Extract the subgraph as a NetworkX object
        subgraph = graph.subgraph(buses_in_subgraph).copy()
        results["details"]["subgraph_nodes"] = subgraph.number_of_nodes()
        results["details"]["subgraph_edges"] = subgraph.number_of_edges()

        # 7. Verify pass condition
        # - Works via native graph primitives or clean NetworkX export: YES
        # - create_nxgraph is documented public API
        # - NetworkX BFS is standard
        # - No workarounds needed
        assert len(buses_in_subgraph) > 0, "No buses found in BFS"
        assert len(lines_in_subgraph) + len(trafos_in_subgraph) > 0, "No branches in subgraph"

        results["status"] = "pass"
        results["details"]["method"] = (
            "pandapower.topology.create_nxgraph(net) -> NetworkX MultiGraph. "
            "BFS via nx.single_source_shortest_path_length(graph, bus, cutoff=3). "
            "Subgraph extraction via graph.subgraph(). All public, documented APIs."
        )
        results["details"]["api_calls_used"] = [
            "pandapower.topology.create_nxgraph(net, respect_switches=True)",
            "networkx.single_source_shortest_path_length(graph, start_bus, cutoff=3)",
            "networkx.bfs_edges(graph, start_bus, depth_limit=3)",
            "graph.subgraph(buses).copy()",
        ]

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
