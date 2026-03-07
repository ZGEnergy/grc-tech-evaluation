"""
Test B-3: Solve N-1 DCPF contingencies. Collect max line loading across all cases.

Dimension: extensibility
Network: MEDIUM (ACTIVSg10k ~10000 buses)
Pass condition: Runs in a loop without re-parsing/re-instantiating the base model.
Notes: MEDIUM: 50 branches (not full N-1 due to network size)
Tool: pandapower v3.4.0
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute N-1 DCPF contingency loop on MEDIUM (50 branches)."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        net = from_mpc(network_file, f_hz=60)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)

        # Build branch list
        branches = []
        for idx in net.line.index:
            branches.append(
                {
                    "type": "line",
                    "idx": int(idx),
                    "from_bus": int(net.line.at[idx, "from_bus"]),
                    "to_bus": int(net.line.at[idx, "to_bus"]),
                }
            )
        for idx in net.trafo.index:
            branches.append(
                {
                    "type": "trafo",
                    "idx": int(idx),
                    "from_bus": int(net.trafo.at[idx, "hv_bus"]),
                    "to_bus": int(net.trafo.at[idx, "lv_bus"]),
                }
            )

        total_branches = len(branches)
        results["details"]["total_branches"] = total_branches

        # Select 50 branches for testing
        n_test = 50
        step = max(1, total_branches // n_test)
        test_branches = branches[::step][:n_test]
        results["details"]["branches_tested"] = len(test_branches)

        # 2. Solve base case
        pp.rundcpp(net)
        assert net["converged"], "Base case DCPF did not converge"

        base_max_loading = 0.0
        if "loading_percent" in net.res_line.columns and len(net.res_line) > 0:
            base_max_loading = float(net.res_line["loading_percent"].max())
        results["details"]["base_case_max_loading_pct"] = base_max_loading

        # 3. N-1 contingency loop
        contingency_results = []
        max_loading_across_all = 0.0
        worst_case_branch = None
        converged_count = 0
        non_converged_count = 0

        solve_start = time.perf_counter()

        for branch in test_branches:
            b_type = branch["type"]
            b_idx = branch["idx"]

            if b_type == "line":
                net.line.at[b_idx, "in_service"] = False
            elif b_type == "trafo":
                net.trafo.at[b_idx, "in_service"] = False

            try:
                pp.rundcpp(net)
                converged = net["converged"]
            except Exception:
                converged = False

            if converged:
                converged_count += 1
                if "loading_percent" in net.res_line.columns and len(net.res_line) > 0:
                    in_service_mask = net.line["in_service"]
                    in_service_loading = net.res_line.loc[in_service_mask, "loading_percent"]
                    case_max_loading = (
                        float(in_service_loading.max()) if len(in_service_loading) > 0 else 0.0
                    )
                else:
                    case_max_loading = 0.0

                if case_max_loading > max_loading_across_all:
                    max_loading_across_all = case_max_loading
                    worst_case_branch = branch
            else:
                non_converged_count += 1
                case_max_loading = None

            contingency_results.append(
                {
                    "branch_type": b_type,
                    "branch_idx": b_idx,
                    "converged": converged,
                    "max_loading_pct": case_max_loading,
                }
            )

            if b_type == "line":
                net.line.at[b_idx, "in_service"] = True
            elif b_type == "trafo":
                net.trafo.at[b_idx, "in_service"] = True

        solve_elapsed = time.perf_counter() - solve_start

        results["details"]["cases_evaluated"] = len(test_branches)
        results["details"]["converged_cases"] = converged_count
        results["details"]["non_converged_cases"] = non_converged_count
        results["details"]["max_loading_across_all_pct"] = max_loading_across_all
        results["details"]["solve_loop_seconds"] = solve_elapsed
        results["details"]["per_case_avg_seconds"] = solve_elapsed / len(test_branches)

        if worst_case_branch:
            results["details"]["worst_case_branch"] = worst_case_branch

        sorted_cases = sorted(
            [c for c in contingency_results if c["max_loading_pct"] is not None],
            key=lambda c: c["max_loading_pct"],
            reverse=True,
        )
        results["details"]["top_5_worst_cases"] = sorted_cases[:5]

        results["details"]["method"] = (
            "In-place branch switching. No model reconstruction per case."
        )
        results["details"]["model_reconstruction_required"] = False

        assert converged_count > 0, "No contingency cases converged"
        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
