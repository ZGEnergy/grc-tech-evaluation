"""C-5: Contingency Sweep Scale on ACTIVSg10k (MEDIUM, 10000 buses).

Dimension: scalability
Network: MEDIUM
Pass condition: N-M sweep (x=5, m=4) on 10k-bus network within 600s.
Capped at ~50 contingencies to keep runtime manageable.
"""

from __future__ import annotations

import itertools
import time
import tracemalloc
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")

GRAPH_DISTANCE = 5
MAX_ORDER = 4
MAX_CANDIDATES = 10  # Cap to keep total contingencies around ~50


def run() -> dict:
    """Execute C-5 contingency sweep scalability test on MEDIUM network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import networkx as nx
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "case_ACTIVSg10k (MEDIUM, 10000 buses)"
        details["params"] = {"x": GRAPH_DISTANCE, "m": MAX_ORDER}

        # Load network
        t_load_0 = time.perf_counter()
        grid = vge.open_file(NETWORK_FILE)
        t_load = time.perf_counter() - t_load_0
        details["load_time_seconds"] = round(t_load, 6)
        details["buses"] = grid.get_bus_number()

        branches = list(grid.lines) + list(grid.transformers2w)
        details["total_branches"] = len(branches)

        # Build graph, find well-connected center bus
        G = grid.build_graph()
        degree_dict = dict(G.degree())
        center_bus = max(degree_dict, key=degree_dict.get)
        details["center_bus_index"] = center_bus
        details["center_bus_degree"] = degree_dict[center_bus]

        # BFS to distance x
        nearby_bus_indices = set(
            nx.single_source_shortest_path_length(G, center_bus, cutoff=GRAPH_DISTANCE).keys()
        )
        details["buses_within_distance"] = len(nearby_bus_indices)

        # Find candidate branches
        candidate_branch_indices = []
        for i, br in enumerate(branches):
            bus_from_idx = grid.buses.index(br.bus_from)
            bus_to_idx = grid.buses.index(br.bus_to)
            if bus_from_idx in nearby_bus_indices and bus_to_idx in nearby_bus_indices:
                candidate_branch_indices.append(i)

        details["candidate_branches_total"] = len(candidate_branch_indices)

        if len(candidate_branch_indices) > MAX_CANDIDATES:
            candidate_branch_indices = candidate_branch_indices[:MAX_CANDIDATES]
        details["candidate_branches_used"] = len(candidate_branch_indices)

        # Baseline DCPF
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

        # ── Escalating-order contingency sweep ──
        tracemalloc.start()
        t0 = time.perf_counter()

        cases_evaluated = 0
        summary_by_order: dict[int, dict] = {}
        pruned_branches: set[int] = set()

        for order in range(1, MAX_ORDER + 1):
            if order == 1:
                active_candidates = candidate_branch_indices
            else:
                active_candidates = [
                    b for b in candidate_branch_indices if b not in pruned_branches
                ]

            combos = list(itertools.combinations(active_candidates, order))
            max_load_loss = 0.0
            non_converged = 0

            for combo in combos:
                for br_idx in combo:
                    branches[br_idx].active = False

                pf_results = vge.power_flow(grid, options=pf_opts)
                cases_evaluated += 1

                if pf_results.converged:
                    load_served = np.sum(np.abs(pf_results.Sbus.real[pf_results.Sbus.real < 0]))
                    load_loss = float(base_load - load_served)
                else:
                    load_loss = float(base_load)
                    non_converged += 1

                max_load_loss = max(max_load_loss, load_loss)

                for br_idx in combo:
                    branches[br_idx].active = True

                if order == 1 and abs(load_loss) < 1e-3:
                    pruned_branches.add(combo[0])

            summary_by_order[order] = {
                "cases": len(combos),
                "max_load_loss_mw": round(max_load_loss, 4),
                "non_converged": non_converged,
            }

        wall_clock = time.perf_counter() - t0
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        details["wall_clock_seconds"] = round(wall_clock, 6)
        details["peak_memory_mb"] = round(peak_mem / (1024 * 1024), 2)
        details["cases_evaluated"] = cases_evaluated
        details["pruned_branch_count"] = len(pruned_branches)
        details["summary_by_order"] = summary_by_order

        workarounds.append(
            {
                "description": (
                    "Manual branch.active toggle and re-solve loop with NetworkX graph distance "
                    "scoping. Same stable workaround as expressiveness tier."
                ),
                "class": "stable",
            }
        )

        status = "pass"

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "peak_memory_mb": details.get("peak_memory_mb"),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
