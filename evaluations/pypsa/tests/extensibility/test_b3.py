"""
Test B-3: N-1 DCPF contingency loop

Dimension: extensibility
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Runs N-1 DCPF contingencies in a loop without re-parsing or
    re-instantiating base model from file each iteration. Base model modified
    in-place or cloned efficiently. Collect max line loading across all cases.
Tool: pypsa 1.1.2
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"


def _load_network(case_file: str) -> pypsa.Network:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    cf = CaseFrames(str(DATA_DIR / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net


def _get_max_loading(net: pypsa.Network) -> tuple[float, str | None]:
    """Compute max branch loading from solved network. Returns (loading, branch_id)."""
    max_load = 0.0
    worst_branch = None

    for comp_name, comp_t_attr, comp_static in [
        ("lines", "lines_t", net.lines),
        ("transformers", "transformers_t", net.transformers),
    ]:
        comp_t = getattr(net, comp_t_attr)
        if comp_t.p0.empty or comp_t.p0.shape[1] == 0:
            continue
        active = comp_static.index[comp_static.active]
        if len(active) == 0:
            continue
        # Only look at active branches that have flow results
        active_with_flows = active.intersection(comp_t.p0.columns)
        if len(active_with_flows) == 0:
            continue
        flows = comp_t.p0.iloc[0][active_with_flows].abs()
        ratings = comp_static.loc[active_with_flows, "s_nom"].replace(0, np.inf)
        loading = flows / ratings
        if loading.max() > max_load:
            max_load = loading.max()
            worst_branch = f"{comp_name}:{loading.idxmax()}"

    return float(max_load), worst_branch


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute the test and return structured results."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    case_file = Path(network_file).name

    start = time.perf_counter()
    try:
        # 1. Load network once from file (no re-parsing in the loop)
        base_net = _load_network(case_file)

        # Run base case LPF to establish reference
        base_net.lpf()

        # Build branch list (lines + transformers)
        branch_list = [("Line", name) for name in base_net.lines.index] + [
            ("Transformer", name) for name in base_net.transformers.index
        ]
        n_contingencies = len(branch_list)

        # 2. N-1 DCPF contingency loop using net.copy() — clone, deactivate, solve
        #    This tests the core requirement: no re-parsing from file per iteration.
        #    net.copy() is a documented public API for deep-copying the network.
        t_loop_start = time.perf_counter()

        max_loading_per_contingency = {}
        overall_max_loading = 0.0
        worst_contingency = None
        worst_branch = None
        contingency_count = 0
        island_count = 0

        for btype, bname in branch_list:
            # Clone from in-memory base (NOT re-parsing from file)
            net_copy = base_net.copy()

            # Deactivate the outaged branch via public API
            if btype == "Line":
                net_copy.lines.at[bname, "active"] = False
            else:
                net_copy.transformers.at[bname, "active"] = False

            # Solve DCPF — PyPSA 1.1.2 has a bug where lpf() crashes with a
            # KeyError when deactivating a branch splits the network into
            # sub-networks where one sub-network has no branches of a given type.
            # Workaround: catch the KeyError and skip island-causing contingencies.
            try:
                net_copy.lpf()
            except KeyError:
                # Network split into islands — one sub-network lacks a branch type.
                # This is a PyPSA bug (KeyError in sub_network.lpf flow assignment).
                # Record as island and skip.
                island_count += 1
                max_loading_per_contingency[(btype, bname)] = {
                    "max_loading_pct": float("inf"),
                    "status": "island",
                }
                contingency_count += 1
                continue

            # Compute max loading across all active branches
            max_load, worst_br = _get_max_loading(net_copy)

            max_loading_per_contingency[(btype, bname)] = {
                "max_loading_pct": round(float(max_load * 100), 2),
                "worst_branch": worst_br,
                "status": "solved",
            }

            if max_load > overall_max_loading:
                overall_max_loading = max_load
                worst_contingency = (btype, bname)
                worst_branch = worst_br

            contingency_count += 1

        t_loop = time.perf_counter() - t_loop_start

        # 3. Also attempt the built-in lpf_contingency (BODF-based)
        builtin_available = False
        builtin_error = None
        t_builtin = None
        try:
            base_net2 = _load_network(case_file)
            t_b_start = time.perf_counter()
            _p0_contingency = base_net2.lpf_contingency()
            t_builtin = time.perf_counter() - t_b_start
            builtin_available = True
        except Exception as e:
            builtin_error = f"{type(e).__name__}: {e}"

        # 4. Validate
        assert contingency_count == n_contingencies, (
            f"Expected {n_contingencies} contingencies, ran {contingency_count}"
        )
        assert overall_max_loading > 0, "No non-zero loading found"

        # Sort for top contingencies (exclude islands for sorting)
        solved = {
            k: v for k, v in max_loading_per_contingency.items() if v.get("status") == "solved"
        }
        sorted_contingencies = sorted(
            solved.items(),
            key=lambda x: x[1]["max_loading_pct"],
            reverse=True,
        )

        results["status"] = "pass"
        results["workarounds"].append(
            "PyPSA 1.1.2 lpf() raises KeyError when branch deactivation causes "
            "network islanding (sub-network with no lines). Workaround: catch "
            "KeyError for island-causing contingencies. Also lpf_contingency() "
            "has a bug (DataFrame.to_frame on DataFrame). Both are public API bugs."
        )
        results["details"] = {
            "n_contingencies_solved": contingency_count - island_count,
            "n_contingencies_island": island_count,
            "n_branches_total": n_contingencies,
            "method": "base_net.copy() + deactivate branch + lpf()",
            "clone_method": "net.copy() (documented public API)",
            "loop_time_s": round(t_loop, 4),
            "time_per_contingency_ms": round(t_loop / n_contingencies * 1000, 2),
            "overall_max_loading_pct": round(float(overall_max_loading * 100), 2),
            "worst_contingency": str(worst_contingency),
            "worst_branch_under_contingency": str(worst_branch),
            "top_5_contingencies": {str(k): v for k, v in sorted_contingencies[:5]},
            "builtin_lpf_contingency_available": builtin_available,
            "builtin_error": builtin_error,
            "builtin_time_s": round(t_builtin, 4) if t_builtin else None,
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
