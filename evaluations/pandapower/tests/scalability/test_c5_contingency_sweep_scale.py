"""
Test C-5: N-M contingency sweep (x=5, m=4) at scale

Dimension: scalability
Network: MEDIUM (ACTIVSg10k, ~10000 buses)
Pass condition: Completes contingency sweep on MEDIUM network.
Tool: pandapower v3.4.0

Parameters: x=5 (graph distance), m=4 (up to 4 simultaneous outages)
Uses DCPF for contingency evaluation (linear, always converges).

Strategy: For large networks, enumerate all combinations naively is infeasible
(~10K branches => C(10K,4) ~ 10^14). Instead, build per-branch neighbor sets
(branches within graph distance x), then enumerate combinations only within
each branch's neighbor group. This is the correct graph-distance-scoped approach.
"""

import json
import os
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc
from pandapower.topology import create_nxgraph


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute N-M contingency sweep at scale and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        max_outages = 4  # m=4
        graph_distance = 5  # x=5

        # 1. Load network
        load_start = time.perf_counter()
        net = from_mpc(network_file, f_hz=60)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        total_branches = len(net.line) + len(net.trafo)
        results["details"]["total_branches"] = total_branches

        # 2. Build graph for distance scoping
        import networkx as nx

        graph_start = time.perf_counter()
        graph = create_nxgraph(net, respect_switches=True)
        graph_elapsed = time.perf_counter() - graph_start
        results["details"]["graph_build_seconds"] = graph_elapsed
        results["details"]["graph_nodes"] = graph.number_of_nodes()
        results["details"]["graph_edges"] = graph.number_of_edges()

        # 3. Solve base case DCPF
        pp.rundcpp(net)
        if not net["converged"]:
            results["errors"].append("Base case DCPF did not converge")
            return results

        base_load = float(net.res_load["p_mw"].sum()) if len(net.load) > 0 else 0.0
        results["details"]["base_case_load_mw"] = base_load

        # 4. Build branch info with index mapping
        branch_info = []
        for idx in net.line.index:
            from_bus = int(net.line.at[idx, "from_bus"])
            to_bus = int(net.line.at[idx, "to_bus"])
            branch_info.append({"type": "line", "idx": idx, "from_bus": from_bus, "to_bus": to_bus})

        for idx in net.trafo.index:
            hv_bus = int(net.trafo.at[idx, "hv_bus"])
            lv_bus = int(net.trafo.at[idx, "lv_bus"])
            branch_info.append({"type": "trafo", "idx": idx, "from_bus": hv_bus, "to_bus": lv_bus})

        n_branches = len(branch_info)

        # 5. Build branch adjacency: for each branch, find all branches within
        #    graph distance x (using bus-level BFS)
        dist_start = time.perf_counter()

        # Map buses to branches that connect to them
        bus_to_branches = {}
        for bi, b in enumerate(branch_info):
            for bus in (b["from_bus"], b["to_bus"]):
                bus_to_branches.setdefault(bus, set()).add(bi)

        # For each branch, compute its neighbor branches via BFS from endpoints
        branch_neighbors = [set() for _ in range(n_branches)]
        for bi, b in enumerate(branch_info):
            nearby_buses = set()
            for bus in (b["from_bus"], b["to_bus"]):
                if bus in graph:
                    lengths = nx.single_source_shortest_path_length(
                        graph, bus, cutoff=graph_distance
                    )
                    nearby_buses.update(lengths.keys())

            # All branches touching nearby buses are neighbors
            for bus in nearby_buses:
                if bus in bus_to_branches:
                    branch_neighbors[bi].update(bus_to_branches[bus])
            # Remove self
            branch_neighbors[bi].discard(bi)

        dist_elapsed = time.perf_counter() - dist_start
        results["details"]["distance_computation_seconds"] = dist_elapsed

        # Stats on neighbor group sizes
        neighbor_sizes = [len(s) for s in branch_neighbors]
        results["details"]["avg_neighbor_group_size"] = (
            sum(neighbor_sizes) / len(neighbor_sizes) if neighbor_sizes else 0
        )
        results["details"]["max_neighbor_group_size"] = max(neighbor_sizes) if neighbor_sizes else 0

        # 6. Enumerate contingency cases using neighbor groups
        #    For order k, for each branch b, enumerate combinations of k-1
        #    branches from b's neighbor set (where all are pairwise neighbors).
        #    Use frozenset to deduplicate.
        prune_start = time.perf_counter()
        pruned_set = set()
        cases_per_order = {}

        # Order 1: all N-1 cases
        for bi in range(n_branches):
            pruned_set.add(frozenset([bi]))
        cases_per_order[1] = len(pruned_set)

        # Order 2: pairs of neighboring branches
        for bi in range(n_branches):
            for bj in branch_neighbors[bi]:
                if bj > bi:  # avoid duplicates
                    pruned_set.add(frozenset([bi, bj]))
        cases_per_order[2] = len(pruned_set) - cases_per_order[1]

        # Order 3: triples where all are pairwise neighbors
        if max_outages >= 3:
            count_before = len(pruned_set)
            for bi in range(n_branches):
                nbrs_i = branch_neighbors[bi]
                nbrs_list = sorted(bj for bj in nbrs_i if bj > bi)
                for j_idx, bj in enumerate(nbrs_list):
                    nbrs_j = branch_neighbors[bj]
                    common = [bk for bk in nbrs_list[j_idx + 1 :] if bk in nbrs_j]
                    for bk in common:
                        pruned_set.add(frozenset([bi, bj, bk]))
            cases_per_order[3] = (
                len(pruned_set) - count_before - cases_per_order[2] - cases_per_order[1]
            )

        # Order 4: quadruples where all are pairwise neighbors
        if max_outages >= 4:
            count_before = len(pruned_set)
            for bi in range(n_branches):
                nbrs_i = branch_neighbors[bi]
                nbrs_list = sorted(bj for bj in nbrs_i if bj > bi)
                for j_idx, bj in enumerate(nbrs_list):
                    nbrs_j = branch_neighbors[bj]
                    common_jk = [bk for bk in nbrs_list[j_idx + 1 :] if bk in nbrs_j]
                    for k_idx, bk in enumerate(common_jk):
                        nbrs_k = branch_neighbors[bk]
                        common_jkl = [bl for bl in common_jk[k_idx + 1 :] if bl in nbrs_k]
                        for bl in common_jkl:
                            pruned_set.add(frozenset([bi, bj, bk, bl]))
            cases_per_order[4] = (
                len(pruned_set) - count_before - sum(cases_per_order.get(k, 0) for k in [1, 2, 3])
            )

        pruned_cases = [tuple(sorted(s)) for s in pruned_set]
        prune_elapsed = time.perf_counter() - prune_start

        results["details"]["pruning_seconds"] = prune_elapsed
        results["details"]["pruned_cases_count"] = len(pruned_cases)
        results["details"]["cases_per_order"] = cases_per_order

        # Compute pruning ratio vs total possible
        from math import comb

        total_possible = sum(comb(n_branches, k) for k in range(1, max_outages + 1))
        results["details"]["total_possible_cases"] = total_possible
        pruning_ratio = 1.0 - (len(pruned_cases) / total_possible) if total_possible > 0 else 0.0
        results["details"]["pruning_ratio"] = pruning_ratio

        # Memory before contingency sweep
        try:
            import resource

            mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # noqa: F841
        except Exception:
            mem_before = None  # noqa: F841

        # 7. Evaluate contingencies (DCPF for each)
        sweep_start = time.perf_counter()
        cases_evaluated = 0
        cases_converged = 0
        cases_with_loss = 0
        max_load_loss = 0.0

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
                    cases_converged += 1
                    served_load = float(net.res_load["p_mw"].sum()) if len(net.load) > 0 else 0.0
                    load_loss = base_load - served_load
                    if abs(load_loss) > 0.01:
                        cases_with_loss += 1
                        max_load_loss = max(max_load_loss, abs(load_loss))
            except Exception:
                pass

            cases_evaluated += 1

            # Re-enable branches
            for b in branches_out:
                if b["type"] == "line":
                    net.line.at[b["idx"], "in_service"] = True
                elif b["type"] == "trafo":
                    net.trafo.at[b["idx"], "in_service"] = True

        sweep_elapsed = time.perf_counter() - sweep_start

        # Memory after sweep
        try:
            mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            results["details"]["peak_memory_mb"] = mem_after
        except Exception:
            pass

        # CPU utilization
        try:
            cpu_times = os.times()
            results["details"]["cpu_user_seconds"] = cpu_times.user
            results["details"]["cpu_system_seconds"] = cpu_times.system
        except Exception:
            pass

        # 8. Record metrics
        results["details"]["total_time_seconds"] = sweep_elapsed
        results["details"]["cases_evaluated"] = cases_evaluated
        results["details"]["cases_converged"] = cases_converged
        results["details"]["cases_with_load_loss"] = cases_with_loss
        results["details"]["max_load_loss_mw"] = max_load_loss
        results["details"]["per_contingency_avg_seconds"] = (
            sweep_elapsed / cases_evaluated if cases_evaluated > 0 else 0
        )

        # 9. Check pass condition
        results["status"] = "pass"
        results["details"]["method"] = (
            "In-place branch switching via net.line/trafo['in_service']. "
            "Graph distance via pandapower.topology.create_nxgraph() + NetworkX BFS. "
            "Neighbor-group enumeration for scalable combinatorial pruning. "
            "No model reconstruction per case."
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
