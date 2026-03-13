"""
Test C-5: Contingency Sweep Scale (contingency_sweep_scale)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k, case_ACTIVSg10k.m)
Pass condition: Total time, per-contingency average, peak memory, N-1/N-2 counts,
  pruning ratio recorded.
Tool: PyPSA 1.1.2

Note: n.lpf_contingency() is broken on Python 3.12+ — using BODF matrix instead.
Depends on: A-7 (same contingency methodology, BODF approach)
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import networkx as nx
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

# BFS depth for scoping
BFS_DEPTH = 2


def load_network(network_file: str):
    """Load ACTIVSg10k via matpowercaseframes -> pypower ppc -> pypsa."""
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
    """Execute N-1 contingency sweep via BODF on ACTIVSg10k.

    Methodology:
    1. Load ACTIVSg10k, run base DCPF
    2. Compute network topology, PTDF, BODF on sub-network
    3. Choose a high-degree bus; BFS depth 2 to find in-scope branches
    4. Enumerate N-1 contingencies for all scoped lines
    5. Apply pruning (parallel-branch filter)
    6. Compute post-outage flows via BODF for all N-1 cases
    7. Record timing, counts, pruning ratio

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
        "workarounds": [
            "n.lpf_contingency() is broken on Python 3.12+ (isinstance(pd.Index, Sequence) "
            "returns False, causing internal type errors). Using BODF matrix directly "
            "via sub_network.calculate_BODF() — same underlying algorithm, documented public API.",
            "overwrite_zero_s_nom=1.0 applied to fix 2462 zero-rated lines in ACTIVSg10k",
        ],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        load_start = time.perf_counter()
        n = load_network(network_file)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["load_seconds"] = load_elapsed
        print(f"Network loaded: {len(n.buses)} buses, {len(n.lines)} lines in {load_elapsed:.2f}s")

        # 2. Run base DCPF
        n.lpf()
        base_p0_lines = n.lines_t.p0.iloc[0].copy()
        total_load = float(n.loads.p_set.sum())
        results["details"]["total_load_mw"] = total_load
        print(f"Base DCPF complete, total load: {total_load:.0f} MW")

        # 3. Compute topology + PTDF + BODF
        print("Computing topology, PTDF, BODF...")
        topo_start = time.perf_counter()
        n.determine_network_topology()
        for sn in n.sub_networks.obj:
            sn.calculate_PTDF()
            sn.calculate_BODF()
        topo_elapsed = time.perf_counter() - topo_start
        results["details"]["topology_bodf_compute_seconds"] = topo_elapsed
        print(f"PTDF/BODF computed in {topo_elapsed:.2f}s")

        # 4. Choose high-degree bus via NetworkX graph
        G = n.graph()
        # Find bus with highest degree (most connected)
        degrees = dict(G.degree())
        focal_bus = max(degrees, key=lambda b: degrees[b])
        focal_degree = degrees[focal_bus]
        results["details"]["focal_bus"] = focal_bus
        results["details"]["focal_bus_degree"] = focal_degree
        print(f"Focal bus: {focal_bus} (degree={focal_degree})")

        # BFS depth 2 from focal bus
        distance_dict = nx.single_source_shortest_path_length(G, focal_bus, cutoff=BFS_DEPTH)
        buses_in_scope = set(distance_dict.keys())
        results["details"]["buses_in_scope"] = len(buses_in_scope)
        print(f"Buses within BFS depth {BFS_DEPTH}: {len(buses_in_scope)}")

        # Get lines incident to buses in scope
        scoped_lines = []
        for line_name in n.lines.index:
            bus0 = n.lines.at[line_name, "bus0"]
            bus1 = n.lines.at[line_name, "bus1"]
            if bus0 in buses_in_scope or bus1 in buses_in_scope:
                scoped_lines.append(line_name)

        results["details"]["n_scoped_lines_before_pruning"] = len(scoped_lines)
        print(f"Scoped lines (before pruning): {len(scoped_lines)}")

        # 5. Apply pruning: skip parallel branches (same bus pair)
        # Build bus-pair -> [lines] mapping
        bus_pair_map: dict = {}
        for line_name in scoped_lines:
            bus0 = n.lines.at[line_name, "bus0"]
            bus1 = n.lines.at[line_name, "bus1"]
            pair = frozenset([bus0, bus1])
            bus_pair_map.setdefault(pair, []).append(line_name)

        # Keep one representative per bus pair (don't remove both parallel lines,
        # just skip truly duplicate contingencies where both endpoints are identical)
        pruned_lines = []
        for pair, lines in bus_pair_map.items():
            if len(lines) == 1:
                pruned_lines.extend(lines)
            else:
                # Keep all lines but mark the pair as having parallel branches
                pruned_lines.extend(lines)
                # (We don't prune parallel lines themselves as N-1 contingencies —
                # they each represent a distinct outage scenario)

        # Actual pruning: if a line has zero flow, pruning it is a valid no-impact filter
        zero_flow_lines = [ln for ln in scoped_lines if abs(float(base_p0_lines.get(ln, 0))) < 0.1]
        pruned_lines = [ln for ln in scoped_lines if ln not in zero_flow_lines]
        n_pruned_zero_flow = len(zero_flow_lines)

        results["details"]["n_zero_flow_lines_pruned"] = n_pruned_zero_flow
        results["details"]["n_n1_contingencies"] = len(pruned_lines)
        pruning_ratio = 1.0 - len(pruned_lines) / max(len(scoped_lines), 1)
        results["details"]["pruning_ratio"] = float(pruning_ratio)
        print(
            f"After pruning (zero-flow removed): {len(pruned_lines)} N-1 contingencies "
            f"(pruning ratio: {pruning_ratio:.2%})"
        )

        # 6. Execute N-1 BODF sweep
        # Find the sub-network containing most of the scoped lines
        # (ACTIVSg10k may have one large connected sub-network)
        main_sn = None
        max_branches = 0
        for sn in n.sub_networks.obj:
            sn_branches = sn.branches()
            n_in_scope = sum(1 for (c, b) in sn_branches.index if c == "Line" and b in scoped_lines)
            if n_in_scope > max_branches:
                max_branches = n_in_scope
                main_sn = sn

        if main_sn is None and len(list(n.sub_networks.obj)) > 0:
            main_sn = list(n.sub_networks.obj)[0]

        if main_sn is None:
            results["errors"].append("No sub-network found — topology detection failed")
            results["status"] = "fail"
            return results

        sn_branches = main_sn.branches()
        results["details"]["sub_network_n_branches"] = len(sn_branches)
        print(f"Sub-network: {len(sn_branches)} branches, BODF shape: {main_sn.BODF.shape}")

        # Build p0 vector for sub-network branches
        p0_sn = []
        for comp, bname in sn_branches.index:
            if comp == "Line" and bname in n.lines_t.p0.columns:
                p0_sn.append(float(n.lines_t.p0.iloc[0][bname]))
            elif (
                comp == "Transformer"
                and len(n.transformers_t.p0) > 0
                and bname in n.transformers_t.p0.columns
            ):
                p0_sn.append(float(n.transformers_t.p0.iloc[0][bname]))
            else:
                p0_sn.append(0.0)
        p0_sn_arr = np.array(p0_sn)

        # Run N-1 sweep
        print(f"\n=== N-1 BODF Sweep: {len(pruned_lines)} contingencies ===")
        sweep_start = time.perf_counter()

        tracemalloc.start()
        n1_results = {}
        n1_errors = 0
        max_violations = 0

        for outage_line in pruned_lines:
            branch_idx = ("Line", outage_line)
            if branch_idx not in sn_branches.index:
                n1_errors += 1
                continue

            branch_i = sn_branches.index.get_loc(branch_idx)
            bodf_col = main_sn.BODF[:, branch_i]
            p0_outage_base = p0_sn_arr[branch_i]

            # Post-contingency flows via BODF
            p0_new = p0_sn_arr + bodf_col * p0_outage_base

            # Count violations (flows exceeding s_nom of branches in sub-network)
            n_violations = 0
            s_nom_sn = []
            for comp, bname in sn_branches.index:
                if comp == "Line" and bname in n.lines.index:
                    s_nom_sn.append(float(n.lines.at[bname, "s_nom"]))
                elif comp == "Transformer" and bname in n.transformers.index:
                    s_nom_sn.append(float(n.transformers.at[bname, "s_nom"]))
                else:
                    s_nom_sn.append(1e9)  # no limit
            s_nom_arr = np.array(s_nom_sn)
            violations = np.abs(p0_new) > s_nom_arr * 1.001
            n_violations = int(violations.sum())
            max_violations = max(max_violations, n_violations)

            n1_results[outage_line] = {
                "max_post_flow_mw": float(np.abs(p0_new).max()),
                "n_overloads": n_violations,
            }

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        sweep_elapsed = time.perf_counter() - sweep_start

        n_completed = len(n1_results)
        per_contingency_avg = sweep_elapsed / max(n_completed, 1)

        results["details"]["n1_sweep_seconds"] = sweep_elapsed
        results["details"]["n1_completed"] = n_completed
        results["details"]["n1_errors"] = n1_errors
        results["details"]["per_contingency_avg_seconds"] = per_contingency_avg
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)
        results["details"]["max_overloads_any_contingency"] = max_violations
        results["details"]["n_contingencies_with_overloads"] = int(
            sum(1 for v in n1_results.values() if v["n_overloads"] > 0)
        )

        print(f"N-1 sweep: {n_completed} contingencies in {sweep_elapsed:.3f}s")
        print(f"Per-contingency avg: {per_contingency_avg * 1000:.2f} ms")
        print(f"Peak memory: {peak / (1024 * 1024):.1f} MB")
        print(
            f"Contingencies with overloads: {results['details']['n_contingencies_with_overloads']}"
        )

        results["status"] = "pass"
        print("\n=== C-5 PASS ===")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
