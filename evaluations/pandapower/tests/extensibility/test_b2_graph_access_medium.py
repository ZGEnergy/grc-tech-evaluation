"""
Test B-2: From a chosen bus, run BFS to depth 3. Return all buses and branches.

Dimension: extensibility
Network: MEDIUM (ACTIVSg10k ~10000 buses)
Pass condition: Works via native graph primitives or clean, documented export to NetworkX.
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.topology import create_nxgraph


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute BFS graph access test on MEDIUM and return structured results."""
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

        # 2. Create NetworkX graph
        graph = create_nxgraph(net, respect_switches=True)
        results["details"]["graph_type"] = type(graph).__name__
        results["details"]["graph_nodes"] = graph.number_of_nodes()
        results["details"]["graph_edges"] = graph.number_of_edges()

        # 3. Choose a starting bus (first bus)
        start_bus = net.bus.index[0]
        bfs_depth = 3
        results["details"]["start_bus"] = int(start_bus)
        results["details"]["bfs_depth"] = bfs_depth

        # 4. Run BFS to depth 3
        distances = dict(nx.single_source_shortest_path_length(graph, start_bus, cutoff=bfs_depth))
        buses_in_subgraph = sorted(distances.keys())
        results["details"]["bus_count_in_subgraph"] = len(buses_in_subgraph)

        bus_depths = {int(bus): int(depth) for bus, depth in distances.items()}
        buses_by_depth = {}
        for bus, depth in bus_depths.items():
            buses_by_depth.setdefault(depth, 0)
            buses_by_depth[depth] += 1
        results["details"]["buses_by_depth"] = buses_by_depth

        # 5. Identify branches in the subgraph
        bus_set = set(buses_in_subgraph)

        lines_in_subgraph = 0
        for idx in net.line.index:
            from_bus = int(net.line.at[idx, "from_bus"])
            to_bus = int(net.line.at[idx, "to_bus"])
            if from_bus in bus_set and to_bus in bus_set:
                lines_in_subgraph += 1

        trafos_in_subgraph = 0
        for idx in net.trafo.index:
            hv_bus = int(net.trafo.at[idx, "hv_bus"])
            lv_bus = int(net.trafo.at[idx, "lv_bus"])
            if hv_bus in bus_set and lv_bus in bus_set:
                trafos_in_subgraph += 1

        results["details"]["line_count_in_subgraph"] = lines_in_subgraph
        results["details"]["trafo_count_in_subgraph"] = trafos_in_subgraph
        results["details"]["total_branches_in_subgraph"] = lines_in_subgraph + trafos_in_subgraph

        # 6. Extract subgraph
        subgraph = graph.subgraph(buses_in_subgraph).copy()
        results["details"]["subgraph_nodes"] = subgraph.number_of_nodes()
        results["details"]["subgraph_edges"] = subgraph.number_of_edges()

        # 7. Pass condition
        assert len(buses_in_subgraph) > 0, "No buses found in BFS"
        assert lines_in_subgraph + trafos_in_subgraph > 0, "No branches in subgraph"

        results["status"] = "pass"
        results["details"]["method"] = (
            "pandapower.topology.create_nxgraph(net) -> NetworkX MultiGraph. "
            "BFS via nx.single_source_shortest_path_length(graph, bus, cutoff=3). "
            "All public, documented APIs."
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
