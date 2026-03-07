"""
Test A-7: N-M contingency sweep with graph-distance scoping and pruning (REDUCED)

Dimension: expressiveness
Network: MEDIUM (ACTIVSg10k ~10000 buses)
Pass condition: Completes without full model reconstruction per contingency case.
Tool: pandapower v3.4.0

REDUCED SCOPE: BFS neighbor computation limited to first 200 branches (of 10,701)
to stay within 5-minute time budget. Full enumeration on 10k branches is O(n^2).
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.topology import create_nxgraph


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute N-M contingency sweep test on MEDIUM (reduced scope)."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    overall_start = time.perf_counter()
    try:
        import networkx as nx

        graph_distance = 5  # x=5
        max_seed_branches = 200  # Limit BFS seed branches for tractability

        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        total_lines = len(net.line)
        total_trafos = len(net.trafo)
        total_branches = total_lines + total_trafos
        results["details"]["total_branches"] = total_branches
        results["details"]["total_lines"] = total_lines
        results["details"]["total_trafos"] = total_trafos

        # 2. Build graph
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

        # 4. Build branch info
        branch_info = []
        for idx in net.line.index:
            from_bus = int(net.line.at[idx, "from_bus"])
            to_bus = int(net.line.at[idx, "to_bus"])
            branch_info.append({"type": "line", "idx": idx, "from_bus": from_bus, "to_bus": to_bus})
        for idx in net.trafo.index:
            hv_bus = int(net.trafo.at[idx, "hv_bus"])
            lv_bus = int(net.trafo.at[idx, "lv_bus"])
            branch_info.append({"type": "trafo", "idx": idx, "from_bus": hv_bus, "to_bus": lv_bus})

        # 5. Build bus-to-branch mapping
        bus_to_branches = {}
        for i, b in enumerate(branch_info):
            for bus in (b["from_bus"], b["to_bus"]):
                bus_to_branches.setdefault(bus, []).append(i)

        # 6. Compute neighbors for a SUBSET of branches (reduced scope)
        seed_indices = list(
            range(0, len(branch_info), max(1, len(branch_info) // max_seed_branches))
        )
        seed_indices = seed_indices[:max_seed_branches]
        results["details"]["seed_branches"] = len(seed_indices)
        results["details"]["scope_note"] = (
            f"BFS neighbor computation limited to {len(seed_indices)} of {total_branches} "
            f"branches for tractability. Full enumeration is O(n^2) on 10k-bus network."
        )

        scope_start = time.perf_counter()
        branch_neighbors = {}
        for bi in seed_indices:
            nearby_buses = set()
            for bus in (branch_info[bi]["from_bus"], branch_info[bi]["to_bus"]):
                if bus in graph:
                    dists = dict(
                        nx.single_source_shortest_path_length(graph, bus, cutoff=graph_distance)
                    )
                    nearby_buses.update(dists.keys())
            nearby_branches = set()
            for bus in nearby_buses:
                if bus in bus_to_branches:
                    nearby_branches.update(bus_to_branches[bus])
            nearby_branches.discard(bi)
            branch_neighbors[bi] = nearby_branches

        scope_time = time.perf_counter() - scope_start
        results["details"]["scope_computation_seconds"] = scope_time

        # 7. Enumerate contingency cases
        enum_start = time.perf_counter()
        pruned_cases = []

        # N-1: all seed branches
        for i in seed_indices:
            pruned_cases.append((i,))

        # N-2: pairs within distance
        for i in seed_indices:
            for j in branch_neighbors.get(i, set()):
                if j > i and j in branch_neighbors:
                    pruned_cases.append((i, j))
                elif j > i:
                    pruned_cases.append((i, j))

        # N-3: triples
        for i in seed_indices:
            nbrs_i = branch_neighbors.get(i, set())
            for j in nbrs_i:
                if j <= i:
                    continue
                nbrs_j = branch_neighbors.get(j, set())
                if not nbrs_j:
                    continue
                common = nbrs_i & nbrs_j
                for k in common:
                    if k > j:
                        pruned_cases.append((i, j, k))

        # N-4: limit to first 2000
        count_k4 = 0
        max_k4 = 2000
        for i in seed_indices:
            if count_k4 >= max_k4:
                break
            nbrs_i = branch_neighbors.get(i, set())
            for j in nbrs_i:
                if j <= i or count_k4 >= max_k4:
                    continue
                nbrs_j = branch_neighbors.get(j, set())
                if not nbrs_j:
                    continue
                common_ij = nbrs_i & nbrs_j
                for m1 in common_ij:
                    if m1 <= j or count_k4 >= max_k4:
                        continue
                    nbrs_m1 = branch_neighbors.get(m1, set())
                    if not nbrs_m1:
                        continue
                    common_ijm = common_ij & nbrs_m1
                    for m2 in common_ijm:
                        if m2 <= m1:
                            continue
                        pruned_cases.append((i, j, m1, m2))
                        count_k4 += 1
                        if count_k4 >= max_k4:
                            break

        enum_time = time.perf_counter() - enum_start
        results["details"]["enum_time_seconds"] = enum_time
        results["details"]["pruned_cases_count"] = len(pruned_cases)

        order_counts = {}
        for combo in pruned_cases:
            k = len(combo)
            order_counts[k] = order_counts.get(k, 0) + 1
        results["details"]["cases_by_order"] = order_counts

        # 8. Evaluate contingencies (cap at 5000)
        max_eval = 5000
        cases_to_eval = pruned_cases[:max_eval]
        results["details"]["cases_to_evaluate"] = len(cases_to_eval)

        solve_start = time.perf_counter()
        cases_evaluated = 0
        non_converged = 0
        cases_with_loss = 0
        max_load_loss = 0.0

        for combo in cases_to_eval:
            branches_out = [branch_info[i] for i in combo]

            for b in branches_out:
                if b["type"] == "line":
                    net.line.at[b["idx"], "in_service"] = False
                elif b["type"] == "trafo":
                    net.trafo.at[b["idx"], "in_service"] = False

            try:
                pp.rundcpp(net)
                converged = net["converged"]
                if converged:
                    served_load = float(net.res_load["p_mw"].sum()) if len(net.load) > 0 else 0.0
                    load_loss = abs(base_load - served_load)
                    if load_loss > 0.01:
                        cases_with_loss += 1
                        max_load_loss = max(max_load_loss, load_loss)
                else:
                    non_converged += 1
            except Exception:
                non_converged += 1

            cases_evaluated += 1

            for b in branches_out:
                if b["type"] == "line":
                    net.line.at[b["idx"], "in_service"] = True
                elif b["type"] == "trafo":
                    net.trafo.at[b["idx"], "in_service"] = True

        solve_elapsed = time.perf_counter() - solve_start

        results["details"]["cases_evaluated"] = cases_evaluated
        results["details"]["cases_non_converged"] = non_converged
        results["details"]["cases_with_load_loss"] = cases_with_loss
        results["details"]["max_load_loss_mw"] = max_load_loss
        results["details"]["solve_loop_seconds"] = solve_elapsed
        results["details"]["per_case_avg_seconds"] = (
            solve_elapsed / cases_evaluated if cases_evaluated > 0 else 0
        )

        results["status"] = "pass"
        results["details"]["method"] = (
            "In-place branch switching via net.line/trafo['in_service']. "
            "Graph distance computed via pandapower.topology.create_nxgraph() "
            "and NetworkX single_source_shortest_path_length. "
            "No model reconstruction per case. "
            "Reduced scope: 200 seed branches of 10,701 total."
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - overall_start

    return results


if __name__ == "__main__":
    start = time.perf_counter()
    result = run()
    print(json.dumps(result, indent=2, default=str))
