"""
Test B-2: Graph access — BFS to depth 3

Dimension: extensibility
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Works via native graph primitives or clean documented export to NetworkX.
    From a chosen bus, run BFS to depth 3, returning all buses and branches within subgraph.
Tool: pypsa 1.1.2
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import networkx as nx
import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"


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
    net.import_from_pypower_ppc(ppc)
    return net


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute the test and return structured results.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    case_file = Path(network_file).name

    start = time.perf_counter()
    try:
        # 1. Load network
        net = _load_network(case_file)

        # 2. Export to NetworkX using PyPSA's documented .graph() method
        #    This is a public, documented API that returns a NetworkX OrderedGraph (MultiGraph)
        G = net.graph()

        # Verify it's a NetworkX graph
        assert isinstance(G, nx.Graph), f"Expected NetworkX graph, got {type(G)}"

        # 3. Pick a starting bus (use the first bus in the index)
        start_bus = str(net.buses.index[0])
        assert start_bus in G.nodes, f"Start bus {start_bus} not in graph nodes"

        # 4. BFS to depth 3 using NetworkX's bfs_edges (standard NetworkX primitive)
        bfs_edges_depth3 = list(nx.bfs_edges(G, start_bus, depth_limit=3))

        # Collect all buses within depth 3
        buses_in_subgraph = {start_bus}
        for u, v in bfs_edges_depth3:
            buses_in_subgraph.add(u)
            buses_in_subgraph.add(v)

        # Also get BFS layers for depth reporting
        bfs_layers = dict(enumerate(nx.bfs_layers(G, start_bus)))
        depth_limited_buses = set()
        for depth in range(4):  # depths 0, 1, 2, 3
            if depth in bfs_layers:
                depth_limited_buses.update(str(b) for b in bfs_layers[depth])

        # 5. Collect branches (edges) within the subgraph
        #    The graph is a MultiGraph, so edges carry (component_type, branch_name) keys
        subgraph_branches = []
        for u, v, key in G.edges(keys=True):
            if u in buses_in_subgraph and v in buses_in_subgraph:
                subgraph_branches.append({"from": u, "to": v, "key": str(key)})

        # 6. Validate results
        assert len(buses_in_subgraph) > 1, "BFS found only the start bus"
        assert len(subgraph_branches) > 0, "No branches found in BFS subgraph"
        # Depth 3 on a 39-bus network should reach a good fraction of buses
        assert len(buses_in_subgraph) <= len(net.buses), "More BFS buses than total buses"

        # 7. Record details
        results["status"] = "pass"
        results["details"] = {
            "graph_type": type(G).__name__,
            "graph_node_count": G.number_of_nodes(),
            "graph_edge_count": G.number_of_edges(),
            "start_bus": start_bus,
            "bfs_depth": 3,
            "buses_found": len(buses_in_subgraph),
            "branches_found": len(subgraph_branches),
            "buses_list": sorted(buses_in_subgraph),
            "depth_layer_sizes": {str(d): len(bfs_layers[d]) for d in range(4) if d in bfs_layers},
            "total_network_buses": len(net.buses),
            "api_used": "net.graph() -> nx.bfs_edges(G, source, depth_limit=3)",
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
