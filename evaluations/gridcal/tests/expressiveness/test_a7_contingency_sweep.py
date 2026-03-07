"""A-7: N-M Contingency Sweep on IEEE 39-bus (TINY).

Enumerate branches within graph distance x=3 of a bus, sweep with escalating
order up to m=3 simultaneous outages with pruning.
"""

from __future__ import annotations

import itertools
import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")

# Parameters for TINY
GRAPH_DISTANCE = 3
MAX_ORDER = 3
LOAD_LOSS_THRESHOLD = 1e-3  # MW — prune if load loss below this


def run() -> dict:
    """Execute A-7 contingency sweep test."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import networkx as nx
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # Load network
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()

        branches = list(grid.lines) + list(grid.transformers2w)
        details["total_branches"] = len(branches)

        # ── Step 1: Build graph and find nearby branches ──
        G = grid.build_graph()
        details["graph_type"] = str(type(G).__name__)
        details["graph_nodes"] = G.number_of_nodes()
        details["graph_edges"] = G.number_of_edges()

        # Choose a bus (use bus 0 for reproducibility)
        center_bus = 0
        center_bus_name = grid.buses[center_bus].name
        details["center_bus_index"] = center_bus
        details["center_bus_name"] = center_bus_name

        # BFS to distance x
        nearby_bus_indices = set(
            nx.single_source_shortest_path_length(G, center_bus, cutoff=GRAPH_DISTANCE).keys()
        )
        details["buses_within_distance"] = len(nearby_bus_indices)

        # Find branches whose both endpoints are within the subgraph
        candidate_branch_indices = []
        for i, br in enumerate(branches):
            bus_from_idx = grid.buses.index(br.bus_from)
            bus_to_idx = grid.buses.index(br.bus_to)
            if bus_from_idx in nearby_bus_indices and bus_to_idx in nearby_bus_indices:
                candidate_branch_indices.append(i)

        details["candidate_branches"] = len(candidate_branch_indices)
        details["candidate_branch_names"] = [branches[i].name for i in candidate_branch_indices]

        # ── Step 2: Baseline DCPF ──
        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
        base_results = vge.power_flow(grid, options=pf_opts)

        if not base_results.converged:
            errors.append("Baseline DCPF did not converge")
            return {
                "status": "fail",
                "wall_clock_seconds": 0,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        base_load = np.sum(np.abs(base_results.Sbus.real[base_results.Sbus.real < 0]))
        details["base_total_load_mw"] = round(float(base_load), 2)

        # ── Step 3: Escalating-order contingency sweep with pruning ──
        t0 = time.perf_counter()

        cases_evaluated = 0
        cases_pruned = 0
        total_possible = 0
        results_by_order: dict[int, list] = {}
        pruned_branches: set[int] = set()  # branches that caused no load loss at order 1

        for order in range(1, MAX_ORDER + 1):
            results_by_order[order] = []

            # Generate combinations, pruning branches that had no impact at lower orders
            if order == 1:
                active_candidates = candidate_branch_indices
            else:
                # Prune: only use branches that caused measurable impact at order 1
                active_candidates = [
                    b for b in candidate_branch_indices if b not in pruned_branches
                ]

            combos = list(itertools.combinations(active_candidates, order))
            total_possible += len(combos)

            for combo in combos:
                # Disable branches
                for br_idx in combo:
                    branches[br_idx].active = False

                # Run DCPF
                pf_results = vge.power_flow(grid, options=pf_opts)
                cases_evaluated += 1

                # Calculate load served
                if pf_results.converged:
                    load_served = np.sum(np.abs(pf_results.Sbus.real[pf_results.Sbus.real < 0]))
                    load_loss = float(base_load - load_served)
                    converged = True
                else:
                    load_loss = float(base_load)  # assume total loss
                    converged = False

                case_result = {
                    "branches_disabled": [branches[i].name for i in combo],
                    "converged": converged,
                    "load_loss_mw": round(load_loss, 4),
                }
                results_by_order[order].append(case_result)

                # Re-enable branches
                for br_idx in combo:
                    branches[br_idx].active = True

                # Pruning logic: at order 1, mark branches with no load loss
                if order == 1 and abs(load_loss) < LOAD_LOSS_THRESHOLD:
                    pruned_branches.add(combo[0])

        wall_clock = time.perf_counter() - t0
        details["wall_clock_seconds"] = round(wall_clock, 6)

        # Compute pruning statistics
        if order > 1:
            possible_without_pruning = sum(
                len(list(itertools.combinations(candidate_branch_indices, o)))
                for o in range(1, MAX_ORDER + 1)
            )
            cases_pruned = possible_without_pruning - total_possible
        else:
            possible_without_pruning = total_possible

        details["cases_evaluated"] = cases_evaluated
        details["cases_pruned"] = cases_pruned
        details["total_possible_without_pruning"] = possible_without_pruning
        details["pruning_ratio"] = (
            round(cases_pruned / possible_without_pruning, 4)
            if possible_without_pruning > 0
            else 0.0
        )
        details["pruned_branch_count"] = len(pruned_branches)

        # Summary per order
        for order in range(1, MAX_ORDER + 1):
            order_results = results_by_order[order]
            details[f"order_{order}_cases"] = len(order_results)
            if order_results:
                max_loss = max(r["load_loss_mw"] for r in order_results)
                details[f"order_{order}_max_load_loss_mw"] = round(max_loss, 4)
                non_converged = sum(1 for r in order_results if not r["converged"])
                details[f"order_{order}_non_converged"] = non_converged

        details["contingency_results"] = results_by_order

        # Workaround documentation
        workarounds.append(
            {
                "description": (
                    "Contingency sweep uses manual branch.active toggle and re-solve loop. "
                    "GridCal has a ContingencyAnalysisDriver but it handles pre-defined "
                    "contingency groups (N-1 only), not arbitrary N-M with pruning logic. "
                    "The manual approach uses public API (branch.active, vge.power_flow) "
                    "and NetworkX graph from grid.build_graph()."
                ),
                "class": "stable",
                "reason": (
                    "Uses documented public API: branch.active toggle, vge.power_flow(), "
                    "grid.build_graph() for NetworkX graph. No internals accessed."
                ),
            }
        )

        details["graph_api_note"] = (
            "grid.build_graph() returns nx.MultiDiGraph with bus indices as nodes "
            "and branches as edges (weight=reactance). NetworkX is a first-class dependency."
        )

        status = "pass"

    except Exception as e:
        errors.append(f"Exception: {type(e).__name__}: {e}")
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    # Print summary without full contingency results (too verbose)
    summary = {k: v for k, v in result.items() if k != "details"}
    summary["details"] = {k: v for k, v in result["details"].items() if k != "contingency_results"}
    print(json.dumps(summary, indent=2, default=str))
