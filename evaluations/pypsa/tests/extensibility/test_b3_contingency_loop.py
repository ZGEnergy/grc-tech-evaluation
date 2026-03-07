"""
Test B-3: Solve N-1 DCPF contingencies, collect max line loading across all cases

Dimension: extensibility
Network: TINY (case39)
Pass condition: Runs in a loop without re-parsing or re-instantiating the base model
    from file each iteration. Base model is modified in-place or cloned efficiently.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")


def _load_network(case_path: str):
    """Load MATPOWER .m file into PyPSA Network via matpowercaseframes."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(case_path)
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


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute N-1 contingency analysis and return structured results.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    try:
        # 1. Load base network once (not timed)
        n_base = _load_network(network_file)

        # Collect all branches (lines + transformers)
        line_names = list(n_base.lines.index)
        transformer_names = list(n_base.transformers.index)
        branch_list = [("Line", name) for name in line_names] + [
            ("Transformer", name) for name in transformer_names
        ]
        n_branches = len(branch_list)

        # Get line ratings for loading calculation
        line_ratings = n_base.lines["s_nom"].copy()
        transformer_ratings = n_base.transformers["s_nom"].copy()

        # 2. Run base case DCPF (not timed separately)
        n_base.lpf()

        # 3. N-1 contingency loop (timed)
        # Strategy: use n.copy() to clone the base network for each contingency,
        # then disable the outaged branch by setting x to very high value (open circuit)
        # This avoids re-reading from file each iteration.
        contingency_results = []
        failed_contingencies = []

        start = time.perf_counter()

        for branch_type, branch_name in branch_list:
            try:
                # Clone efficiently via n.copy()
                n_cont = n_base.copy()

                # Disable the branch by removing it
                if branch_type == "Line":
                    n_cont.lines.loc[branch_name, "s_nom"] = 0.0
                    n_cont.lines.loc[branch_name, "x"] = 1e10  # Open circuit
                else:
                    n_cont.transformers.loc[branch_name, "s_nom"] = 0.0
                    n_cont.transformers.loc[branch_name, "x"] = 1e10

                # Run DCPF on contingency case
                n_cont.lpf()

                # Compute line loading (|flow| / rating) for remaining branches
                cont_line_flows = n_cont.lines_t.p0.iloc[0]
                cont_transformer_flows = n_cont.transformers_t.p0.iloc[0]

                # Max loading across all lines (excluding outaged branch)
                max_loading = 0.0
                max_loading_branch = ""

                for lname in line_names:
                    if branch_type == "Line" and lname == branch_name:
                        continue  # Skip outaged line
                    rating = line_ratings[lname]
                    if rating > 0:
                        loading = abs(cont_line_flows[lname]) / rating
                        if loading > max_loading:
                            max_loading = loading
                            max_loading_branch = f"Line-{lname}"

                for tname in transformer_names:
                    if branch_type == "Transformer" and tname == branch_name:
                        continue
                    rating = transformer_ratings[tname]
                    if rating > 0:
                        loading = abs(cont_transformer_flows[tname]) / rating
                        if loading > max_loading:
                            max_loading = loading
                            max_loading_branch = f"Transformer-{tname}"

                contingency_results.append(
                    {
                        "outage": f"{branch_type}-{branch_name}",
                        "max_loading_pct": max_loading * 100,
                        "max_loading_branch": max_loading_branch,
                        "converged": True,
                    }
                )

            except Exception as e:
                failed_contingencies.append(
                    {
                        "outage": f"{branch_type}-{branch_name}",
                        "error": f"{type(e).__name__}: {e}",
                    }
                )

        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed

        # 4. Aggregate results
        n_converged = len(contingency_results)
        n_failed = len(failed_contingencies)

        if contingency_results:
            df = pd.DataFrame(contingency_results)
            worst_case = df.loc[df["max_loading_pct"].idxmax()]
            overloaded = df[df["max_loading_pct"] > 100.0]

            # Top 5 worst contingencies
            top5 = df.nlargest(5, "max_loading_pct")[
                ["outage", "max_loading_pct", "max_loading_branch"]
            ].to_dict("records")
        else:
            worst_case = None
            overloaded = pd.DataFrame()
            top5 = []

        # 5. Pass condition: loop runs without re-parsing from file,
        #    base model modified in-place or cloned efficiently
        pass_condition_met = (
            n_converged > 0
            and n_converged == n_branches  # All contingencies solved
            and n_failed == 0
        )

        if pass_condition_met:
            results["status"] = "pass"

        results["details"] = {
            "total_branches": n_branches,
            "n_lines": len(line_names),
            "n_transformers": len(transformer_names),
            "contingencies_solved": n_converged,
            "contingencies_failed": n_failed,
            "time_per_contingency_ms": (elapsed / n_branches * 1000) if n_branches > 0 else None,
            "clone_method": "n.copy() — deep copy without re-reading file",
            "outage_method": "Set x=1e10 (open circuit) on outaged branch",
            "worst_contingency": {
                "outage": str(worst_case["outage"]) if worst_case is not None else None,
                "max_loading_pct": (
                    float(worst_case["max_loading_pct"]) if worst_case is not None else None
                ),
                "max_loading_branch": (
                    str(worst_case["max_loading_branch"]) if worst_case is not None else None
                ),
            },
            "n_overloaded_cases": len(overloaded),
            "top_5_worst": top5,
            "failed_contingencies": failed_contingencies,
            "lpf_contingency_bug": (
                "n.lpf_contingency() exists but crashes with AttributeError "
                "('DataFrame' has no 'to_frame') in v1.1.2. Manual loop used instead."
            ),
        }

        if failed_contingencies:
            results["workarounds"].append(
                f"{n_failed} contingencies failed — see failed_contingencies in details"
            )

        results["workarounds"].append(
            "Used n.copy() + manual branch disabling loop instead of n.lpf_contingency() "
            "which has a bug in v1.1.2 (AttributeError: 'DataFrame' has no 'to_frame')"
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
