"""
Test B-3: Solve N-1 DCPF contingencies. Collect max line loading across all cases.

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Runs in a loop without re-parsing/re-instantiating the base model
    each iteration. Base model modified in-place or cloned efficiently.
Notes: TINY: all 46 branches (full N-1)
Tool: pandapower v3.4.0

APPROACH: Use in-place branch switching via net.line.at[idx, 'in_service'] = False
and net.trafo.at[idx, 'in_service'] = False. Solve rundcpp(), collect results,
restore. No model reconstruction per case.
"""

import json
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute N-1 DCPF contingency loop test and return structured results."""
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

        # Build branch list (lines + trafos)
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

        # 2. Solve base case DCPF
        pp.rundcpp(net)
        assert net["converged"], "Base case DCPF did not converge"
        results["details"]["base_case_converged"] = True

        # Record base case max line loading
        base_max_loading = 0.0
        if "loading_percent" in net.res_line.columns and len(net.res_line) > 0:
            base_max_loading = float(net.res_line["loading_percent"].max())
        results["details"]["base_case_max_loading_pct"] = base_max_loading

        # Base case line flows for reference
        base_max_flow_mw = (
            float(net.res_line["p_from_mw"].abs().max()) if len(net.res_line) > 0 else 0
        )
        results["details"]["base_case_max_flow_mw"] = base_max_flow_mw

        # 3. N-1 contingency loop (in-place branch switching)
        contingency_results = []
        max_loading_across_all = 0.0
        worst_case_branch = None
        converged_count = 0
        non_converged_count = 0

        solve_start = time.perf_counter()

        for branch in branches:
            b_type = branch["type"]
            b_idx = branch["idx"]

            # Disable branch in-place (no model reconstruction)
            if b_type == "line":
                net.line.at[b_idx, "in_service"] = False
            elif b_type == "trafo":
                net.trafo.at[b_idx, "in_service"] = False

            # Solve DCPF
            try:
                pp.rundcpp(net)
                converged = net["converged"]
            except Exception:
                converged = False

            if converged:
                converged_count += 1
                # Collect max line loading
                if "loading_percent" in net.res_line.columns and len(net.res_line) > 0:
                    # Only consider in-service lines
                    in_service_mask = net.line["in_service"]
                    in_service_loading = net.res_line.loc[in_service_mask, "loading_percent"]
                    if len(in_service_loading) > 0:
                        case_max_loading = float(in_service_loading.max())
                    else:
                        case_max_loading = 0.0
                else:
                    case_max_loading = 0.0

                # Also get max absolute flow
                if len(net.res_line) > 0:
                    in_service_flows = net.res_line.loc[net.line["in_service"], "p_from_mw"].abs()
                    case_max_flow = (
                        float(in_service_flows.max()) if len(in_service_flows) > 0 else 0
                    )
                else:
                    case_max_flow = 0.0

                if case_max_loading > max_loading_across_all:
                    max_loading_across_all = case_max_loading
                    worst_case_branch = branch
            else:
                non_converged_count += 1
                case_max_loading = None
                case_max_flow = None

            contingency_results.append(
                {
                    "branch_type": b_type,
                    "branch_idx": b_idx,
                    "from_bus": branch["from_bus"],
                    "to_bus": branch["to_bus"],
                    "converged": converged,
                    "max_loading_pct": case_max_loading,
                    "max_flow_mw": case_max_flow,
                }
            )

            # Restore branch (in-place)
            if b_type == "line":
                net.line.at[b_idx, "in_service"] = True
            elif b_type == "trafo":
                net.trafo.at[b_idx, "in_service"] = True

        solve_elapsed = time.perf_counter() - solve_start

        # 4. Compile results
        results["details"]["cases_evaluated"] = total_branches
        results["details"]["converged_cases"] = converged_count
        results["details"]["non_converged_cases"] = non_converged_count
        results["details"]["max_loading_across_all_pct"] = max_loading_across_all
        results["details"]["max_flow_mw_across_converged"] = max(
            (c["max_flow_mw"] for c in contingency_results if c["max_flow_mw"] is not None),
            default=0.0,
        )

        if worst_case_branch:
            results["details"]["worst_case_branch"] = worst_case_branch

        # Top 5 worst contingencies by loading
        sorted_cases = sorted(
            [c for c in contingency_results if c["max_loading_pct"] is not None],
            key=lambda c: c["max_loading_pct"],
            reverse=True,
        )
        results["details"]["top_5_worst_cases"] = sorted_cases[:5]

        # Timing
        results["details"]["solve_loop_seconds"] = solve_elapsed
        results["details"]["per_case_avg_seconds"] = (
            solve_elapsed / total_branches if total_branches > 0 else 0
        )

        # Method documentation
        results["details"]["method"] = (
            "In-place branch switching via net.line/trafo.at[idx, 'in_service'] = False. "
            "No model reconstruction or re-parsing per contingency case. "
            "Base model modified in-place, solved with pp.rundcpp(), then restored."
        )
        results["details"]["model_reconstruction_required"] = False

        # 5. Check pass condition
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
