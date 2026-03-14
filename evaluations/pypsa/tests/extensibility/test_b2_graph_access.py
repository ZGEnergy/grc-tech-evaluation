"""
Test B-2: From a chosen bus, run BFS to depth 3 on TINY

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Works via native graph primitives or clean, documented export to
  NetworkX (Python) or Graphs.jl (Julia).
Tool: PyPSA 1.1.2
"""

import sys
import time
import traceback
from pathlib import Path

import networkx as nx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute BFS graph traversal from a chosen bus to depth 3.

    Uses PyPSA's documented n.graph() method which returns a NetworkX MultiGraph,
    then runs standard NetworkX BFS.
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        from matpower_loader import load_pypsa

        # 1. Load network
        n = load_pypsa(network_file)

        # 2. Get NetworkX graph via documented API: n.graph()
        #    Returns a networkx.MultiGraph where buses are nodes and
        #    branches (lines + transformers) are edges
        G = n.graph()

        results["details"]["graph_type"] = type(G).__name__
        results["details"]["n_nodes"] = G.number_of_nodes()
        results["details"]["n_edges"] = G.number_of_edges()
        results["details"]["graph_method"] = "n.graph() -> NetworkX MultiGraph (documented API)"

        # 3. Choose root bus and run BFS to depth 3
        root = "1"
        if root not in G.nodes:
            # Try numeric bus name
            root = 1
        assert root in G.nodes, f"Bus '{root}' not in graph nodes: {list(G.nodes)[:10]}..."

        # BFS: all nodes reachable within depth 3
        depths = nx.single_source_shortest_path_length(G, root, cutoff=3)
        reachable = set(depths.keys())

        # Organize by depth level
        by_depth = {}
        for node, d in depths.items():
            by_depth.setdefault(d, []).append(node)

        # Subgraph induced by reachable nodes
        subgraph = G.subgraph(reachable)
        buses_in_subgraph = sorted(subgraph.nodes())
        edges_in_subgraph = list(subgraph.edges(keys=True))
        branch_names = sorted([key for _, _, key in edges_in_subgraph])

        results["details"]["root_bus"] = str(root)
        results["details"]["bfs_depth"] = 3
        results["details"]["buses_by_depth"] = {
            str(d): sorted([str(b) for b in nodes]) for d, nodes in sorted(by_depth.items())
        }
        results["details"]["n_buses_in_subgraph"] = len(buses_in_subgraph)
        results["details"]["n_edges_in_subgraph"] = len(edges_in_subgraph)
        results["details"]["buses_in_subgraph"] = [str(b) for b in buses_in_subgraph]
        results["details"]["branches_in_subgraph"] = branch_names

        # 4. Verify correctness
        assert str(root) in [str(b) for b in buses_in_subgraph], (
            f"Root bus {root} not in BFS subgraph"
        )
        assert len(buses_in_subgraph) > 1, "BFS subgraph has only root (no neighbors)"
        assert len(edges_in_subgraph) > 0, "BFS subgraph has no edges"

        # Additional graph primitives available via documented API
        results["details"]["additional_graph_apis"] = [
            "n.adjacency_matrix()",
            "n.incidence_matrix()",
            "n.determine_network_topology()",
        ]

        # Lines of code for graph access: n.graph() + bfs + subgraph = 3 substantive lines
        results["details"]["loc_graph_access"] = 3

        print(f"Graph type: {type(G).__name__}")
        print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
        print(f"BFS from bus '{root}' depth 3:")
        for d in sorted(by_depth.keys()):
            print(f"  Depth {d}: {sorted([str(b) for b in by_depth[d]])}")
        print(f"Subgraph: {len(buses_in_subgraph)} buses, {len(edges_in_subgraph)} edges")

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
