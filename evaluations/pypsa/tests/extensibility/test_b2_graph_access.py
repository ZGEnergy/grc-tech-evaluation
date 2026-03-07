"""
Test B-2: Graph Access

Dimension: extensibility
Network: TINY (case39)
Pass condition: Works via native graph primitives or clean, documented export to NetworkX (Python).
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback

import pypsa
from matpowercaseframes import CaseFrames


def _load_network(case_path: str) -> pypsa.Network:
    """Load MATPOWER .m file into PyPSA Network."""
    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    try:
        ppc["gencost"] = cf.gencost.values
    except Exception:
        pass
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    return n


def run(network_file: str = "/workspace/data/networks/case39.m") -> dict:
    """Execute the test and return structured results.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
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
        n = _load_network(network_file)

        # 2. Get NetworkX graph via n.graph()
        G = n.graph()
        results["details"]["graph_type"] = type(G).__name__
        results["details"]["graph_nodes"] = G.number_of_nodes()
        results["details"]["graph_edges"] = G.number_of_edges()

        # 3. Pick a starting bus (first bus)
        start_bus = list(G.nodes())[0]
        results["details"]["start_bus"] = str(start_bus)

        # 4. BFS to depth 3 using NetworkX
        bfs_tree = nx.bfs_tree(G, start_bus, depth_limit=3)
        bfs_buses = list(bfs_tree.nodes())
        results["details"]["bfs_depth"] = 3
        results["details"]["bfs_bus_count"] = len(bfs_buses)
        results["details"]["bfs_buses"] = [str(b) for b in bfs_buses]

        # 5. Extract the subgraph (buses and branches within BFS tree)
        subgraph = G.subgraph(bfs_buses).copy()
        results["details"]["subgraph_nodes"] = subgraph.number_of_nodes()
        results["details"]["subgraph_edges"] = subgraph.number_of_edges()

        # 6. Get edges (branches) in the subgraph
        subgraph_edges = list(subgraph.edges(data=True))
        results["details"]["subgraph_branch_count"] = len(subgraph_edges)
        results["details"]["subgraph_branches"] = [
            {"from": str(u), "to": str(v), "type": str(d.get("type", "unknown"))}
            for u, v, d in subgraph_edges[:10]  # first 10 for display
        ]

        # 7. Verify BFS correctness: start bus should be in result
        assert start_bus in bfs_buses, "Start bus not in BFS result"
        # All nodes should be reachable within 3 hops
        for node in bfs_buses:
            path_len = nx.shortest_path_length(G, start_bus, node)
            assert path_len <= 3, f"Node {node} is {path_len} hops away, expected <= 3"

        # Count lines of code for the core operation (graph + BFS + subgraph)
        results["details"]["loc"] = (
            4  # G = n.graph(); bfs_tree = nx.bfs_tree(...); subgraph = G.subgraph(...).copy()
        )

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
