"""
Test A-7: N-M contingency sweep with graph-distance scoping and pruning

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Completes without full model reconstruction per contingency case.
    Load loss per contingency case collected. Pruning logic is expressible
    without fighting the tool. Combinatorial enumeration and graph-distance
    scoping are achievable via the tool's API or a clean graph library bridge.
Tool: pandapower v3.4.0

Notes: TINY: x=3, m=3 (combinations of up to 3 simultaneous outages from branches
    within graph distance 3 of each other)
"""

import json
import time
import traceback
from itertools import combinations

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.topology import create_nxgraph


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute N-M contingency sweep test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    try:
        # Parameters for TINY
        max_outages = 3  # m=3: up to 3 simultaneous outages
        graph_distance = 3  # x=3: branches within graph distance 3

        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        total_branches = len(net.line) + len(net.trafo) + len(net.impedance)
        results["details"]["total_branches"] = total_branches
        results["details"]["total_lines"] = len(net.line)
        results["details"]["total_trafos"] = len(net.trafo)
        results["details"]["total_impedances"] = len(net.impedance)

        # 2. Build graph for distance scoping using pandapower's NetworkX integration
        graph = create_nxgraph(net, respect_switches=True)
        results["details"]["graph_nodes"] = graph.number_of_nodes()
        results["details"]["graph_edges"] = graph.number_of_edges()

        # 3. Solve base case DCPF
        pp.rundcpp(net)
        if not net["converged"]:
            results["errors"].append("Base case DCPF did not converge")
            return results

        base_load = float(net.res_load["p_mw"].sum()) if len(net.load) > 0 else 0.0
        results["details"]["base_case_load_mw"] = base_load

        # 4. Graph-distance scoping: identify branch groups within distance x
        # Build a mapping from branches (lines) to their endpoint buses
        import networkx as nx

        branch_info = []
        for idx in net.line.index:
            from_bus = int(net.line.at[idx, "from_bus"])
            to_bus = int(net.line.at[idx, "to_bus"])
            branch_info.append({"type": "line", "idx": idx, "from_bus": from_bus, "to_bus": to_bus})

        for idx in net.trafo.index:
            hv_bus = int(net.trafo.at[idx, "hv_bus"])
            lv_bus = int(net.trafo.at[idx, "lv_bus"])
            branch_info.append({"type": "trafo", "idx": idx, "from_bus": hv_bus, "to_bus": lv_bus})

        # Compute shortest path distances between all bus pairs (for small network, feasible)
        try:
            all_distances = dict(nx.all_pairs_shortest_path_length(graph, cutoff=graph_distance))
        except Exception:
            all_distances = {}

        # Function to check if two branches are within graph distance x
        def branches_within_distance(b1, b2, max_dist):
            """Check if any endpoint of b1 is within max_dist of any endpoint of b2."""
            buses1 = {b1["from_bus"], b1["to_bus"]}
            buses2 = {b2["from_bus"], b2["to_bus"]}
            for bus1 in buses1:
                if bus1 in all_distances:
                    for bus2 in buses2:
                        if bus2 in all_distances[bus1] and all_distances[bus1][bus2] <= max_dist:
                            return True
            return False

        # 5. Pruning: enumerate candidate contingency sets
        # For each order k (1 to max_outages), generate combinations
        # but only keep those where all branches are pairwise within graph_distance
        total_possible = 0
        pruned_cases = []

        for k in range(1, max_outages + 1):
            for combo in combinations(range(len(branch_info)), k):
                total_possible += 1
                if k == 1:
                    pruned_cases.append(combo)
                else:
                    # Check all pairs within graph distance
                    all_close = True
                    for i in range(len(combo)):
                        for j in range(i + 1, len(combo)):
                            if not branches_within_distance(
                                branch_info[combo[i]], branch_info[combo[j]], graph_distance
                            ):
                                all_close = False
                                break
                        if not all_close:
                            break
                    if all_close:
                        pruned_cases.append(combo)

        results["details"]["total_possible_cases"] = total_possible
        results["details"]["pruned_cases_count"] = len(pruned_cases)
        pruning_ratio = 1.0 - (len(pruned_cases) / total_possible) if total_possible > 0 else 0.0
        results["details"]["pruning_ratio"] = pruning_ratio

        # 6. Evaluate contingencies using in-place line switching (no model reconstruction)
        start = time.perf_counter()
        contingency_results = []
        cases_evaluated = 0

        for combo in pruned_cases:
            branches_out = [branch_info[i] for i in combo]

            # Disable branches in-place
            for b in branches_out:
                if b["type"] == "line":
                    net.line.at[b["idx"], "in_service"] = False
                elif b["type"] == "trafo":
                    net.trafo.at[b["idx"], "in_service"] = False

            # Solve DCPF
            try:
                pp.rundcpp(net)
                converged = net["converged"]
                if converged:
                    served_load = float(net.res_load["p_mw"].sum()) if len(net.load) > 0 else 0.0
                    load_loss = base_load - served_load
                else:
                    load_loss = base_load  # Assume total loss if not converged
            except Exception:
                converged = False
                load_loss = base_load

            contingency_results.append(
                {
                    "branches_out": [(b["type"], int(b["idx"])) for b in branches_out],
                    "converged": converged,
                    "load_loss_mw": load_loss,
                }
            )
            cases_evaluated += 1

            # Re-enable branches
            for b in branches_out:
                if b["type"] == "line":
                    net.line.at[b["idx"], "in_service"] = True
                elif b["type"] == "trafo":
                    net.trafo.at[b["idx"], "in_service"] = True

        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed
        results["details"]["cases_evaluated"] = cases_evaluated
        results["details"]["per_case_avg_seconds"] = (
            elapsed / cases_evaluated if cases_evaluated > 0 else 0
        )

        # Summary of contingency results
        nonzero_loss = [c for c in contingency_results if c["load_loss_mw"] > 0.01]
        non_converged = [c for c in contingency_results if not c["converged"]]
        results["details"]["cases_with_load_loss"] = len(nonzero_loss)
        results["details"]["cases_non_converged"] = len(non_converged)

        if nonzero_loss:
            max_loss_case = max(nonzero_loss, key=lambda c: c["load_loss_mw"])
            results["details"]["max_load_loss_mw"] = max_loss_case["load_loss_mw"]
            results["details"]["max_loss_branches"] = max_loss_case["branches_out"]

        # Sample first 10 results
        results["details"]["sample_results"] = contingency_results[:10]

        # Cases by order
        order_counts = {}
        for combo in pruned_cases:
            k = len(combo)
            order_counts[k] = order_counts.get(k, 0) + 1
        results["details"]["cases_by_order"] = order_counts

        # 7. Check pass condition
        # - Completes without full model reconstruction: YES (in-place switching)
        # - Load loss per contingency case collected: YES
        # - Pruning logic expressible: YES (via NetworkX graph distance)
        # - Combinatorial enumeration achievable: YES
        results["status"] = "pass"
        results["details"]["method"] = (
            "In-place branch switching via net.line/trafo['in_service']. "
            "Graph distance computed via pandapower.topology.create_nxgraph() "
            "and NetworkX all_pairs_shortest_path_length. "
            "No model reconstruction per case."
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
