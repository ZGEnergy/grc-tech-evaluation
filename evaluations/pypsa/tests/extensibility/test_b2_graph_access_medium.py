"""
Test B-2: Graph Access — BFS from chosen bus

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: n.graph() returns a NetworkX graph. BFS from a chosen bus
  to depth 3 completes correctly. Subgraph is constructible from BFS result.
Tool: PyPSA 1.1.2
"""

import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=1.0)
    return n


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute BFS graph access test on 10k-bus network.

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
        import networkx as nx

        # 1. Load network
        print("Loading 10k network...")
        n = load_network(network_file)
        print(
            f"Loaded: {len(n.buses)} buses, {len(n.lines)} lines, {len(n.transformers)} transformers"
        )

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)

        # 2. Get graph
        t_graph_start = time.perf_counter()
        G = n.graph()
        t_graph_elapsed = time.perf_counter() - t_graph_start

        graph_type = type(G).__name__
        n_nodes = G.number_of_nodes()
        n_edges = G.number_of_edges()
        print(
            f"Graph: type={graph_type}, nodes={n_nodes}, edges={n_edges}, t={t_graph_elapsed:.4f}s"
        )

        results["details"]["graph_type"] = graph_type
        results["details"]["graph_nodes"] = n_nodes
        results["details"]["graph_edges"] = n_edges
        results["details"]["graph_build_seconds"] = t_graph_elapsed

        # 3. Choose a root bus — use a well-connected bus (first bus or a high-degree one)
        # Pick bus with highest degree for interesting BFS result
        degree_dict = dict(G.degree())
        root = max(degree_dict, key=lambda b: degree_dict[b])
        root_degree = degree_dict[root]
        print(f"Root bus: {root} (degree={root_degree})")
        results["details"]["bfs_root"] = str(root)
        results["details"]["bfs_root_degree"] = root_degree

        # 4. BFS from root to depth 3
        t_bfs_start = time.perf_counter()
        reachable_depth = nx.single_source_shortest_path_length(G, root, cutoff=3)
        reachable = set(reachable_depth.keys())
        subgraph = G.subgraph(reachable)
        t_bfs_elapsed = time.perf_counter() - t_bfs_start

        subgraph_nodes = subgraph.number_of_nodes()
        subgraph_edges = subgraph.number_of_edges()
        print(
            f"BFS depth=3: {subgraph_nodes} buses, {subgraph_edges} branches, "
            f"t={t_bfs_elapsed:.4f}s"
        )

        results["details"]["bfs_depth"] = 3
        results["details"]["bfs_reachable_buses"] = subgraph_nodes
        results["details"]["bfs_reachable_branches"] = subgraph_edges
        results["details"]["bfs_seconds"] = t_bfs_elapsed

        # 5. Depth distribution
        depth_counts: dict[int, int] = {}
        for d in reachable_depth.values():
            depth_counts[d] = depth_counts.get(d, 0) + 1
        results["details"]["bfs_depth_distribution"] = {
            str(k): v for k, v in sorted(depth_counts.items())
        }
        print(f"BFS depth distribution: {depth_counts}")

        # 6. Verify pass conditions
        errors = []
        if not isinstance(G, nx.Graph):
            errors.append(f"n.graph() did not return a NetworkX graph — got {type(G)}")
        if n_nodes != len(n.buses):
            errors.append(f"Graph nodes ({n_nodes}) != n_buses ({len(n.buses)})")
        if n_edges != len(n.lines) + len(n.transformers):
            errors.append(
                f"Graph edges ({n_edges}) != n_lines+n_xfmrs ({len(n.lines) + len(n.transformers)})"
            )
        if subgraph_nodes == 0:
            errors.append("BFS returned empty subgraph")
        if subgraph_nodes == 1:
            errors.append("BFS returned only the root bus — connectivity issue?")

        results["errors"].extend(errors)
        if not errors:
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
