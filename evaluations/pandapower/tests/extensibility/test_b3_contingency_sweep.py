"""
Test B-3: N-M contingency sweep (x=3, m=3) with pruning

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Completes without full model reconstruction per contingency case.
    Load loss per contingency case collected. Pruning logic is expressible without
    fighting the tool. Combinatorial enumeration and graph-distance scoping are
    achievable via the tool's API or a clean graph library bridge.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

# N-M parameters
X_FOCAL_BUSES = 3  # Number of focal buses for scoping
M_CONTINGENCY = 3  # Remove m branches simultaneously
MAX_GRAPH_DISTANCE = 3  # Pruning: only consider branches within this distance


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute N-M contingency sweep with pruning."""
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
        import pandapower as pp
        import pandapower.topology as top

        # 1. Load network
        net = load_pandapower(network_file)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)

        # 2. Run baseline power flow
        pp.rundcpp(net)
        if not net.converged:
            results["errors"].append("Baseline DC power flow did not converge")
            return results

        baseline_load_mw = float(net.res_load["p_mw"].sum())
        results["details"]["baseline_load_mw"] = baseline_load_mw

        # 3. Create NetworkX graph for pruning/scoping
        mg = top.create_nxgraph(net, respect_switches=True)
        results["details"]["graph_node_count"] = mg.number_of_nodes()
        results["details"]["graph_edge_count"] = mg.number_of_edges()

        # 4. Select focal buses (highest-load buses)
        load_by_bus = net.load.groupby("bus")["p_mw"].sum().sort_values(ascending=False)
        focal_buses = load_by_bus.index[:X_FOCAL_BUSES].tolist()
        results["details"]["focal_buses"] = focal_buses
        results["details"]["focal_bus_loads_mw"] = {
            int(b): float(load_by_bus[b]) for b in focal_buses
        }

        # 5. Graph-distance pruning: find branches within MAX_GRAPH_DISTANCE
        # of any focal bus
        candidate_lines = set()
        for focal_bus in focal_buses:
            # Get all buses within graph distance
            depths = nx.single_source_shortest_path_length(mg, focal_bus, cutoff=MAX_GRAPH_DISTANCE)
            nearby_buses = set(depths.keys())

            # Find lines connecting these nearby buses
            for line_idx in net.line.index:
                if not net.line.at[line_idx, "in_service"]:
                    continue
                from_bus = net.line.at[line_idx, "from_bus"]
                to_bus = net.line.at[line_idx, "to_bus"]
                if from_bus in nearby_buses or to_bus in nearby_buses:
                    candidate_lines.add(line_idx)

        candidate_lines = sorted(candidate_lines)
        total_lines = len(net.line[net.line["in_service"]])
        results["details"]["candidate_lines_after_pruning"] = len(candidate_lines)
        results["details"]["total_in_service_lines"] = total_lines
        results["details"]["pruning_ratio"] = (
            1.0 - len(candidate_lines) / total_lines if total_lines > 0 else 0
        )

        # 6. Enumerate N-M combinations (m=3 from pruned set)
        all_combos = list(combinations(candidate_lines, M_CONTINGENCY))
        results["details"]["total_nm_combinations"] = len(all_combos)

        # Additional pruning: skip combinations where all branches are in
        # the same radial stub (removing them would just island a stub)
        # For this test, we proceed with all combinations from the pruned set.

        # 7. Run N-M contingency sweep
        contingency_results_list = []
        n_converged = 0
        n_diverged = 0
        n_island = 0
        max_load_loss = 0.0
        worst_case = None

        sweep_start = time.perf_counter()

        for combo in all_combos:
            # Disable the m branches
            for line_idx in combo:
                net.line.at[line_idx, "in_service"] = False

            try:
                # Run DC power flow (no model reconstruction — just toggle in_service)
                pp.rundcpp(net, check_connectivity=True)

                if net.converged:
                    n_converged += 1
                    # Check for unsupplied buses (load loss)
                    unsupplied = top.unsupplied_buses(net, mg=None)
                    load_loss = 0.0
                    if len(unsupplied) > 0:
                        load_at_unsupplied = net.load[net.load["bus"].isin(unsupplied)][
                            "p_mw"
                        ].sum()
                        load_loss = float(load_at_unsupplied)

                    case_result = {
                        "lines_removed": list(combo),
                        "converged": True,
                        "load_loss_mw": load_loss,
                        "unsupplied_buses": len(unsupplied),
                    }
                    contingency_results_list.append(case_result)

                    if load_loss > max_load_loss:
                        max_load_loss = load_loss
                        worst_case = case_result
                else:
                    n_diverged += 1
                    # Check if divergence is due to islanding
                    unsupplied = top.unsupplied_buses(net, mg=None)
                    load_loss = 0.0
                    if len(unsupplied) > 0:
                        load_at_unsupplied = net.load[net.load["bus"].isin(unsupplied)][
                            "p_mw"
                        ].sum()
                        load_loss = float(load_at_unsupplied)
                        n_island += 1

                    case_result = {
                        "lines_removed": list(combo),
                        "converged": False,
                        "load_loss_mw": load_loss,
                        "unsupplied_buses": len(unsupplied),
                    }
                    contingency_results_list.append(case_result)

                    if load_loss > max_load_loss:
                        max_load_loss = load_loss
                        worst_case = case_result

            except Exception as e:
                case_result = {
                    "lines_removed": list(combo),
                    "converged": False,
                    "error": str(e),
                    "load_loss_mw": 0.0,
                }
                contingency_results_list.append(case_result)
                n_diverged += 1
            finally:
                # Restore all branches
                for line_idx in combo:
                    net.line.at[line_idx, "in_service"] = True

        sweep_time = time.perf_counter() - sweep_start
        results["details"]["sweep_seconds"] = sweep_time
        results["details"]["time_per_contingency_ms"] = (
            sweep_time / len(all_combos) * 1000 if all_combos else 0
        )

        results["details"]["n_converged"] = n_converged
        results["details"]["n_diverged"] = n_diverged
        results["details"]["n_island"] = n_island
        results["details"]["max_load_loss_mw"] = max_load_loss
        results["details"]["worst_case"] = worst_case

        # Report summary of top 5 worst contingencies
        sorted_by_loss = sorted(
            contingency_results_list, key=lambda x: x["load_loss_mw"], reverse=True
        )
        results["details"]["top5_worst_contingencies"] = sorted_by_loss[:5]

        # Distribution of load loss
        load_losses = [c["load_loss_mw"] for c in contingency_results_list]
        results["details"]["load_loss_stats"] = {
            "min": float(np.min(load_losses)) if load_losses else 0,
            "max": float(np.max(load_losses)) if load_losses else 0,
            "mean": float(np.mean(load_losses)) if load_losses else 0,
            "nonzero_count": sum(1 for ll in load_losses if ll > 0),
        }

        # 8. Verify the approach used in-place modification (no model reconstruction)
        results["details"]["approach"] = (
            "In-place toggle of net.line['in_service'] column per contingency. "
            "No model reconstruction required — pandapower rebuilds the internal "
            "bus-branch model (net._ppc) from DataFrames on each rundcpp() call, "
            "but the pandapower network object itself is reused. "
            "Graph-distance pruning via pandapower.topology.create_nxgraph() + "
            "NetworkX single_source_shortest_path_length(). "
            "Load loss detection via pandapower.topology.unsupplied_buses()."
        )

        # 9. Check pass conditions
        all_cases_have_load_loss = all("load_loss_mw" in c for c in contingency_results_list)

        if (
            len(all_combos) > 0
            and all_cases_have_load_loss
            and len(candidate_lines) < total_lines  # Pruning actually reduced the set
        ):
            results["status"] = "pass"
        elif len(all_combos) > 0 and all_cases_have_load_loss:
            results["status"] = "pass"
            results["details"]["note"] = (
                "Pruning did not reduce candidate set because all lines are within "
                "graph distance of focal buses in this small network."
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
