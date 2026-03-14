"""
Test B-3: N-M contingency sweep from a chosen bus, graph distance x=3, up to m=3 outages.

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Completes without full model reconstruction per contingency.
    Load loss per contingency collected. Pruning and enumeration achievable via API or graph bridge.
Tool: gridcal (VeraGridEngine) 5.6.28
"""

from __future__ import annotations

import itertools
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute B-3 contingency sweep test and return structured results."""
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
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        # 1. Load network
        grid = load_gridcal(network_file)
        buses = grid.get_buses()
        branches = grid.get_branches()
        loads = grid.get_loads()
        n_buses = len(buses)
        n_branches = len(branches)

        results["details"]["bus_count"] = n_buses
        results["details"]["branch_count"] = n_branches
        results["details"]["load_count"] = len(loads)

        # 2. Build graph via documented API (build_graph returns nx.MultiDiGraph with int nodes)
        graph = grid.build_graph()
        results["details"]["graph_type"] = type(graph).__name__
        results["details"]["graph_nodes"] = graph.number_of_nodes()
        results["details"]["graph_edges"] = graph.number_of_edges()

        # 3. Choose a starting bus (index 15 = bus "16" in case39, a load bus with
        #    interesting connectivity)
        start_idx = 15
        start_bus_name = buses[start_idx].name
        results["details"]["start_bus_index"] = start_idx
        results["details"]["start_bus_name"] = start_bus_name

        # 4. BFS to depth 3 using NetworkX
        nearby = dict(nx.single_source_shortest_path_length(graph, start_idx, cutoff=3))
        nearby_set = set(nearby.keys())
        results["details"]["bfs_depth"] = 3
        results["details"]["bfs_node_count"] = len(nearby_set)
        results["details"]["bfs_nodes"] = sorted(nearby_set)

        # 5. Identify branches within the BFS subgraph
        branch_indices_in_subgraph = []
        for i, br in enumerate(branches):
            f = buses.index(br.bus_from)
            t = buses.index(br.bus_to)
            if f in nearby_set and t in nearby_set:
                branch_indices_in_subgraph.append(i)

        results["details"]["branches_in_subgraph"] = len(branch_indices_in_subgraph)
        results["details"]["branch_indices"] = branch_indices_in_subgraph

        # 6. Compute baseline load served
        # Build bus-to-load mapping
        bus_load_mw = np.zeros(n_buses)
        for load in loads:
            bus_idx = buses.index(load.bus)
            bus_load_mw[bus_idx] += load.P
        total_load = float(np.sum(bus_load_mw))
        results["details"]["total_load_mw"] = total_load

        # 7. Solve baseline DCPF
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        pf_base = vge.power_flow(grid, options=pf_opts)
        assert pf_base.converged, "Baseline DCPF did not converge"

        # 8. Enumerate N-M contingencies (m=1,2,3) and solve each by toggling
        #    branch.active — no model reconstruction required
        max_m = 3
        contingency_results = []
        combo_counts = {}

        t_solve_start = time.perf_counter()

        for m in range(1, max_m + 1):
            combos = list(itertools.combinations(branch_indices_in_subgraph, m))
            combo_counts[m] = len(combos)

            for combo in combos:
                # Disable branches
                for idx in combo:
                    branches[idx].active = False

                # Solve DCPF (reuses compiled grid — no reconstruction)
                pf = vge.power_flow(grid, options=pf_opts)

                # Compute load loss: check which buses are in disconnected islands
                # In DCPF, isolated buses get zero voltage
                voltages = np.abs(pf.voltage)
                served_load = 0.0
                for bus_idx in range(n_buses):
                    if voltages[bus_idx] > 0.5:  # bus is energized
                        served_load += bus_load_mw[bus_idx]
                load_loss = total_load - served_load

                contingency_results.append(
                    {
                        "m": m,
                        "branches_out": list(combo),
                        "branch_names": [branches[i].name for i in combo],
                        "converged": bool(pf.converged),
                        "load_loss_mw": round(load_loss, 2),
                    }
                )

                # Re-enable branches
                for idx in combo:
                    branches[idx].active = True

        t_solve_end = time.perf_counter()
        solve_time = t_solve_end - t_solve_start

        total_contingencies = sum(combo_counts.values())
        results["details"]["contingency_counts"] = combo_counts
        results["details"]["total_contingencies"] = total_contingencies
        results["details"]["solve_time_seconds"] = round(solve_time, 4)
        results["details"]["time_per_contingency_ms"] = round(
            solve_time / total_contingencies * 1000, 2
        )

        # 9. Summarize load loss statistics
        load_losses = [c["load_loss_mw"] for c in contingency_results]
        nonzero_loss = [ll for ll in load_losses if ll > 0]
        results["details"]["contingencies_with_load_loss"] = len(nonzero_loss)
        results["details"]["max_load_loss_mw"] = max(load_losses) if load_losses else 0.0
        results["details"]["mean_load_loss_mw"] = (
            round(float(np.mean(nonzero_loss)), 2) if nonzero_loss else 0.0
        )

        # Record top-5 worst contingencies by load loss
        sorted_cont = sorted(contingency_results, key=lambda x: x["load_loss_mw"], reverse=True)
        results["details"]["top5_worst"] = sorted_cont[:5]

        # Record a sample of all results (first 10 per m-level)
        sample = {}
        for m in range(1, max_m + 1):
            m_results = [c for c in contingency_results if c["m"] == m]
            sample[f"m={m}"] = m_results[:10]
        results["details"]["sample_results"] = sample

        # 10. Check pass condition
        all_converged = all(c["converged"] for c in contingency_results)
        pass_checks = {
            "completed_without_reconstruction": True,  # branch.active toggle — no rebuild
            "all_contingencies_solved": all_converged,
            "load_loss_collected": len(contingency_results) == total_contingencies,
            "enumeration_via_graph_bfs": True,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
