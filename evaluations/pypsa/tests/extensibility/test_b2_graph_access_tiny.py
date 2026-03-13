"""
Test B-2: Graph Access — BFS from chosen bus

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Works via native graph primitives or clean, documented export to NetworkX.
Tool: PyPSA 1.1.2
"""

import time
import traceback
from pathlib import Path

import networkx as nx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")


def load_network(network_file: str):
    """Load case39.m via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute BFS graph traversal from bus '1' to depth 3.

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

    start = time.perf_counter()
    try:
        # 1. Load network
        n = load_network(network_file)

        # 2. Get NetworkX graph — n.graph() returns a networkx.MultiGraph
        #    Buses are nodes, branches (lines + transformers) are edges
        G = n.graph()

        results["details"]["graph_type"] = type(G).__name__
        results["details"]["n_nodes"] = G.number_of_nodes()
        results["details"]["n_edges"] = G.number_of_edges()

        # 3. Choose root bus '1' and run BFS to depth 3
        root = "1"
        assert root in G.nodes, f"Bus '{root}' not in graph nodes"

        # All nodes reachable within depth 3
        reachable = set(nx.single_source_shortest_path_length(G, root, cutoff=3).keys())

        # Subgraph induced by reachable nodes — edges within depth-3 subgraph
        subgraph = G.subgraph(reachable)

        buses_in_subgraph = list(subgraph.nodes())
        edges_in_subgraph = list(subgraph.edges(keys=True))

        results["details"]["root_bus"] = root
        results["details"]["bfs_depth"] = 3
        results["details"]["n_buses_in_subgraph"] = len(buses_in_subgraph)
        results["details"]["n_edges_in_subgraph"] = len(edges_in_subgraph)
        results["details"]["buses_in_subgraph"] = sorted(buses_in_subgraph)
        # Extract branch names (edge keys in MultiGraph)
        branch_names = [key for _, _, key in edges_in_subgraph]
        results["details"]["branches_in_subgraph"] = sorted(branch_names)

        # 4. Verify correctness: root must be in subgraph, subgraph must be non-trivial
        assert root in buses_in_subgraph, f"Root bus {root} not in BFS subgraph"
        assert len(buses_in_subgraph) > 1, "BFS subgraph has only root bus (no neighbors found)"
        assert len(edges_in_subgraph) > 0, "BFS subgraph has no edges"

        # 5. Count lines of code for the graph access operation
        # (n.graph() call + BFS call + subgraph extraction = 3 substantive lines)
        results["details"]["loc_graph_access"] = 3  # n.graph(); bfs_tree; subgraph

        print(f"Graph type: {type(G).__name__}")
        print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
        print(f"BFS from bus '{root}' depth 3:")
        print(f"  Buses in subgraph ({len(buses_in_subgraph)}): {sorted(buses_in_subgraph)}")
        print(f"  Branches in subgraph ({len(edges_in_subgraph)}): {sorted(branch_names)}")

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
